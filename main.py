import logging
import os
import random
import sqlite3
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
)

# ==========================================
# 1. CONFIGURATION & TOKEN DIRECT
# ==========================================

TOKEN = "8027243153:AAGJleVVHIt5QYouPSUuOd025MKPzYjJHtM"

OWNER_ID = 6559674906

super_admins = {OWNER_ID}
moderateurs = set()

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)

MAX_MONEY = 10_000_000_000_000  # Limite anti-montants gigantesques
cooldowns = {}  # Dictionnaire global pour gérer les cooldowns (anti-spam)


def check_cooldown(uid: int, action: str, secondes: int) -> int:
    """Vérifie si un utilisateur est en cooldown pour une action donnée. Retourne les secondes restantes."""
    now = datetime.now().timestamp()
    key = f"{uid}_{action}"
    dernier = cooldowns.get(key, 0)
    ecoule = now - dernier
    if ecoule < secondes:
        return int(secondes - ecoule)
    cooldowns[key] = now
    return 0


# ==========================================
# 2. BASE DE DONNÉES SQLITE - MODE WAL + ROW_FACTORY
# ==========================================

db = sqlite3.connect("mafiacity.db", check_same_thread=False)
db.row_factory = sqlite3.Row  # Utilisation des dictionnaires pour les lignes SQL
db.execute("PRAGMA journal_mode=WAL")
db.execute("PRAGMA foreign_keys=ON")

with db:
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY,
        name TEXT,
        cash INTEGER DEFAULT 50000,
        bank INTEGER DEFAULT 0,
        xp INTEGER DEFAULT 0,
        level INTEGER DEFAULT 1,
        energy INTEGER DEFAULT 100,
        job TEXT DEFAULT 'Sans emploi',
        health INTEGER DEFAULT 100,
        married_to INTEGER DEFAULT NULL,
        diploma TEXT DEFAULT 'Aucun',
        shield INTEGER DEFAULT 0,
        last_daily TEXT DEFAULT NULL
    );

    CREATE TABLE IF NOT EXISTS bans(
        user_id INTEGER PRIMARY KEY
    );

    CREATE TABLE IF NOT EXISTS logs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action TEXT,
        timestamp TEXT
    );

    CREATE TABLE IF NOT EXISTS loans(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        amount INTEGER,
        interest INTEGER,
        loan_date TEXT
    );

    CREATE TABLE IF NOT EXISTS inventory(
        user_id INTEGER,
        item TEXT,
        amount INTEGER DEFAULT 0,
        PRIMARY KEY(user_id,item)
    );

    CREATE TABLE IF NOT EXISTS user_stocks(
        user_id INTEGER,
        symbol TEXT,
        shares INTEGER,
        PRIMARY KEY(user_id, symbol)
    );

    CREATE TABLE IF NOT EXISTS market(
        item TEXT PRIMARY KEY,
        price INTEGER,
        stock INTEGER
    );

    CREATE TABLE IF NOT EXISTS stock_market(
        symbol TEXT PRIMARY KEY,
        name TEXT,
        price INTEGER
    );

    CREATE INDEX IF NOT EXISTS idx_cash ON users(cash);
    CREATE INDEX IF NOT EXISTS idx_level ON users(level);

    INSERT OR IGNORE INTO market(item, price, stock) VALUES
    ('Cannabis', 500, 1000), ('Cocaïne', 2000, 500), ('Arme lourde', 15000, 50);

    INSERT OR IGNORE INTO stock_market(symbol, name, price) VALUES
    ('MAFIA', 'MafiaCorp', 15000), ('GUNS', 'Armes & Cie', 30000), ('CAS', 'Casino Royale', 7500);
    """)


# ==========================================
# 3. FONCTIONS UTILITAIRES & TÂCHES DE FOND
# ==========================================

def log_action(texte):
    try:
        with db:
            db.execute("INSERT INTO logs(action, timestamp) VALUES(?, ?)", (texte, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    except Exception as e:
        logging.error(f"Erreur lors de l'enregistrement du log : {e}")

async def cleanup_logs_job(context: ContextTypes.DEFAULT_TYPE):
    try:
        limite_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
        with db:
            db.execute("DELETE FROM logs WHERE timestamp < ?", (limite_date,))
        logging.info("🧹 Nettoyage automatique des vieux logs effectué.")
    except Exception as e:
        logging.error(f"Erreur dans cleanup_logs_job : {e}")

async def regenerate_energy_job(context: ContextTypes.DEFAULT_TYPE):
    try:
        with db:
            db.execute("UPDATE users SET energy = MIN(energy + 10, 100) WHERE health > 0")
        logging.info("⚡ Régénération automatique de l'énergie effectuée.")
    except Exception as e:
        logging.error(f"Erreur dans regenerate_energy_job : {e}")

def est_banni(uid):
    cur = db.cursor()
    cur.execute("SELECT user_id FROM bans WHERE user_id=?", (uid,))
    return cur.fetchone() is not None

def get_player(user_or_id, name="Inconnu"):
    """Récupère un joueur par son objet User ou son ID numérique, le crée si inexistant."""
    if hasattr(user_or_id, "id"):
        uid = user_or_id.id
        uname = user_or_id.first_name
    else:
        uid = int(user_or_id)
        uname = name

    cur = db.cursor()
    cur.execute("SELECT * FROM users WHERE id=?", (uid,))
    data = cur.fetchone()
    if data is None:
        with db:
            db.execute("INSERT OR IGNORE INTO users(id, name) VALUES(?,?)", (uid, uname))
        cur.execute("SELECT * FROM users WHERE id=?", (uid,))
        data = cur.fetchone()
    return data

def add_cash(uid, money):
    if money <= 0 or money > MAX_MONEY:
        return
    with db:
        db.execute("INSERT OR IGNORE INTO users(id, name) VALUES(?, 'Inconnu')", (uid,))
        db.execute("UPDATE users SET cash = MIN(cash + ?, ?) WHERE id = ?", (money, MAX_MONEY, uid))

def remove_cash(uid, amount):
    if amount <= 0 or amount > MAX_MONEY:
        return False
    cur = db.cursor()
    with db:
        cur.execute("""
            UPDATE users 
            SET cash = cash - ? 
            WHERE id = ? AND cash >= ?
        """, (amount, uid, amount))
    return cur.rowcount > 0

def add_health(uid, amount):
    with db:
        db.execute("UPDATE users SET health=MIN(MAX(health+?, 0), 100) WHERE id=?", (amount, uid))

def add_xp(uid, xp_gained):
    if xp_gained <= 0:
        return
    cur = db.cursor()
    cur.execute("SELECT xp, level FROM users WHERE id=?", (uid,))
    row = cur.fetchone()
    if not row:
        return
    xp_now, level = row["xp"], row["level"]
    xp_now += xp_gained
    need = level * 100
    
    while xp_now >= need:
        xp_now -= need
        level += 1
        need = level * 100
        
    with db:
        db.execute("UPDATE users SET xp=?, level=? WHERE id=?", (xp_now, level, uid))

async def update_stock_market(context: ContextTypes.DEFAULT_TYPE):
    try:
        cur = db.cursor()
        cur.execute("SELECT symbol, price FROM stock_market")
        stocks = cur.fetchall()
        with db:
            for row in stocks:
                symbol, price = row["symbol"], row["price"]
                variation = random.uniform(-0.10, 0.12)
                nouveau_prix = int(price * (1 + variation))
                nouveau_prix = max(100, min(1000000, nouveau_prix))
                db.execute("UPDATE stock_market SET price=? WHERE symbol=?", (nouveau_prix, symbol))
        logging.info("📈 Les cours de la bourse ont fluctué.")
    except Exception as e:
        logging.error(f"Erreur dans update_stock_market : {e}")


# ==========================================
# 4. COMMANDES DE BASE & AIDE
# ==========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if est_banni(uid): return
    get_player(update.effective_user)
    await update.message.reply_text("🌆 Bienvenue dans *Mafia City* !\n\nUtilise /help pour voir la liste des commandes.", parse_mode="Markdown")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texte = (
        "📜 *Commandes Mafia City (Actives)*\n\n"
        "👤 `/me` | 💰 `/acc` | 🎁 `/daily` | 🛠 `/work` | 💤 `/sleep`\n"
        "💸 `/pay` | 🏆 `/top` | 🏦 `/bank`\n"
        "📥 `/deposit` | 📤 `/withdraw` | 💳 `/loan` | 🏷 `/rembourser`\n"
        "🎓 `/diplome` | 🛒 `/shop` | 🛡 `/gilet`\n"
        "🎰 `/slots` | 🎲 `/dice` | 🥷 `/steal`\n"
        "💍 `/mariage` | 💔 `/divorce`\n"
        "💼 `/metier` | 💊 `/marche_noire` | 🛒 `/buyblack` | 🎒 `/inventory` | 💵 `/sellblack` | 🏥 `/hopital`\n"
        "📈 `/bourse` | 📊 `/portfolio` | 📈 `/invest` | 💸 `/sellstock`"
    )
    await update.message.reply_text(texte, parse_mode="Markdown")

async def me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user)
    shield_status = "🛡 Actif" if p["shield"] > 0 else "❌ Inactif"
    await update.message.reply_text(
        f"👤 *{p['name']}*\n\n"
        f"💵 Cash : {p['cash']:,} €\n"
        f"🏦 Banque : {p['bank']:,} €\n"
        f"⭐ Niveau : {p['level']} (XP: {p['xp']})\n"
        f"⚡ Énergie : {p['energy']}\n"
        f"💼 Métier : {p['job']}\n"
        f"❤️ Santé : {p['health']}/100\n"
        f"🎓 Diplôme : {p['diploma']}\n"
        f"🛡 Gilet pare-balles : {shield_status}",
        parse_mode="Markdown"
    )

async def acc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user)
    await update.message.reply_text(f"💰 Cash : *{p['cash']:,} €* | 🏦 Banque : *{p['bank']:,} €*", parse_mode="Markdown")

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cur = db.cursor()
    cur.execute("SELECT name, cash + bank as total FROM users ORDER BY total DESC LIMIT 5")
    classement = cur.fetchall()
    txt = "🏆 *Top 5 des Parrains les plus riches*\n\n"
    for i, row in enumerate(classement, 1):
        txt += f"{i}. *{row['name']}* — {row['total']:,} €\n"
    await update.message.reply_text(txt, parse_mode="Markdown")

async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if est_banni(uid): return
    p = get_player(update.effective_user)
    
    maintenant = datetime.now()
    if p["last_daily"]:
        dernier_daily = datetime.strptime(p["last_daily"], '%Y-%m-%d %H:%M:%S')
        if maintenant - dernier_daily < timedelta(days=1):
            restant = timedelta(days=1) - (maintenant - dernier_daily)
            heures, minutes = divmod(int(restant.total_seconds()), 3600)
            minutes //= 60
            await update.message.reply_text(f"⏳ Récompense déjà récupérée. Reviens dans {heures}h {minutes}m.")
            return

    with db:
        db.execute("UPDATE users SET cash = cash + 25000, last_daily = ? WHERE id = ?", (maintenant.strftime('%Y-%m-%d %H:%M:%S'), uid))
    
    add_xp(uid, 15)
    log_action(f"Récompense daily récupérée par {uid}")
    await update.message.reply_text("🎁 Récompense récupérée !\n\n+25 000 € | +15 XP")


# ==========================================
# 5. BANQUE, ARGENT & PRÊTS
# ==========================================

async def bank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user)
    await update.message.reply_text(f"🏦 *Compte Bancaire*\n\nSolde : {p['bank']:,} €\n\nUtilise `/deposit <montant>` ou `/withdraw <montant>`", parse_mode="Markdown")

async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if est_banni(uid): return
    if not context.args:
        await update.message.reply_text("Utilisation : `/deposit <montant>`", parse_mode="Markdown")
        return
    try:
        montant = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Montant invalide.")
        return
    if montant <= 0 or montant > MAX_MONEY: 
        await update.message.reply_text("❌ Montant invalide ou trop élevé.")
        return

    p = get_player(update.effective_user)
    if p["cash"] < montant:
        await update.message.reply_text("❌ Pas assez de cash.")
        return
    
    with db:
        db.execute("UPDATE users SET cash = cash - ?, bank = bank + ? WHERE id = ? AND cash >= ?", (montant, montant, uid, montant))
    log_action(f"Dépôt bancaire de {montant}€ par {uid}")
    await update.message.reply_text(f"📥 Dépôt de {montant:,} € effectué.")

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if est_banni(uid): return
    if not context.args:
        await update.message.reply_text("Utilisation : `/withdraw <montant>`", parse_mode="Markdown")
        return
    try:
        montant = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Montant invalide.")
        return
    if montant <= 0 or montant > MAX_MONEY: 
        await update.message.reply_text("❌ Montant invalide.")
        return

    p = get_player(update.effective_user)
    if p["bank"] < montant:
        await update.message.reply_text("❌ Pas assez d'argent en banque.")
        return
    
    with db:
        db.execute("UPDATE users SET bank = bank - ?, cash = cash + ? WHERE id = ? AND bank >= ?", (montant, montant, uid, montant))
    log_action(f"Retrait bancaire de {montant}€ par {uid}")
    await update.message.reply_text(f"📤 Retrait de {montant:,} € effectué.")

async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if est_banni(uid): return
    
    reste = check_cooldown(uid, "pay", 3)
    if reste > 0:
        await update.message.reply_text(f"⏳ Patiente encore {reste}s.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Utilisation : `/pay <id_joueur> <montant>`", parse_mode="Markdown")
        return
    try:
        cible, montant = int(context.args[0]), int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Paramètres invalides.")
        return
        
    if cible == OWNER_ID:
        await update.message.reply_text("❌ Impossible d'effectuer cette action sur le propriétaire du bot.")
        return

    if montant <= 0 or montant > MAX_MONEY or cible == uid: 
        await update.message.reply_text("❌ Montant invalide ou cible incorrecte.")
        return

    if est_banni(cible):
        await update.message.reply_text("❌ Impossible d'envoyer de l'argent à un joueur banni.")
        return

    get_player(cible, name="Inconnu")
        
    if not remove_cash(uid, montant):
        await update.message.reply_text("❌ Cash insuffisant.")
        return
        
    add_cash(cible, montant)
    log_action(f"Virement de {montant}€ de {uid} vers {cible}")
    await update.message.reply_text(f"💸 Virement de {montant:,} € effectué vers `{cible}`.", parse_mode="Markdown")

async def loan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if est_banni(uid): return

    reste = check_cooldown(uid, "loan", 10)
    if reste > 0:
        await update.message.reply_text(f"⏳ Patiente encore {reste}s.")
        return

    cur = db.cursor()
    cur.execute("SELECT * FROM loans WHERE user_id=?", (uid,))
    if cur.fetchone():
        await update.message.reply_text("❌ Tu as déjà un prêt en cours !")
        return
    
    date_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with db:
        db.execute("INSERT OR IGNORE INTO loans(user_id, amount, interest, loan_date) VALUES(?,?,?,?)", (uid, 50000, 55000, date_now))
        db.execute("UPDATE users SET cash = cash + 50000 WHERE id = ?", (uid,))
    log_action(f"Prêt accordé à {uid} (50000€)")
    await update.message.reply_text("💳 Prêt accordé de 50 000 €. Remboursement via `/rembourser`.", parse_mode="Markdown")

async def rembourser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if est_banni(uid): return
    
    cur = db.cursor()
    cur.execute("SELECT amount, interest, loan_date FROM loans WHERE user_id=?", (uid,))
    loan_data = cur.fetchone()
    if not loan_data:
        await update.message.reply_text("✅ Tu n'as aucun prêt en cours.")
        return
    
    date_pret = datetime.strptime(loan_data["loan_date"], '%Y-%m-%d %H:%M:%S')
    jours_ecoules = (datetime.now() - date_pret).days
    total_du = loan_data["interest"] + (jours_ecoules * 2000)

    if not remove_cash(uid, total_du):
        await update.message.reply_text(f"❌ Il te faut {total_du:,} € en cash pour rembourser.")
        return
        
    with db:
        db.execute("DELETE FROM loans WHERE user_id=?", (uid,))
    log_action(f"Prêt remboursé par {uid}")
    await update.message.reply_text("✅ Prêt entièrement remboursé !")


# ==========================================
# 6. MÉTIERS, SHOP, ÉNERGIE & SOMMEIL
# ==========================================

METIERS = {
    "medecin": {"salaire": 35000, "desc": "Soigne les blessés."},
    "avocat": {"salaire": 40000, "desc": "Défend les criminels."},
    "chauffeur": {"salaire": 25000, "desc": "Transporte des colis."}
}

async def metier(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if est_banni(uid): return
    if not context.args:
        txt = "💼 Métiers disponibles :\n\n" + "".join([f"• *{k}* : {v['desc']} (Salaire: {v['salaire']:,} €)\n" for k, v in METIERS.items()]) + "\nUtilise `/metier <nom>`"
        await update.message.reply_text(txt, parse_mode="Markdown")
        return
    nom_metier = context.args[0].lower()
    if nom_metier not in METIERS:
        await update.message.reply_text("❌ Métier inconnu.")
        return
    with db:
        db.execute("UPDATE users SET job=? WHERE id=?", (nom_metier, uid))
    await update.message.reply_text(f"✅ Nouveau métier : *{nom_metier}*", parse_mode="Markdown")

async def work(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if est_banni(uid): return

    reste = check_cooldown(uid, "work", 5)
    if reste > 0:
        await update.message.reply_text(f"⏳ Tu dois souffler un peu ({reste}s).")
        return

    p = get_player(update.effective_user)
    
    if p["health"] <= 0:
        await update.message.reply_text("❌ Tu es inconscient ! Utilise /hopital pour te soigner.")
        return
    if p["energy"] < 10:
        await update.message.reply_text("❌ Trop fatigué (Énergie < 10). Utilise `/sleep`.")
        return

    salaire = METIERS.get(p["job"], {"salaire": 15000})["salaire"]
    
    with db:
        db.execute("UPDATE users SET cash = cash + ?, energy = MAX(energy - 10, 0) WHERE id = ?", (salaire, uid))
    
    add_xp(uid, 10)
        
    await update.message.reply_text(f"🛠 Travail effectué (Énergie -10).\n\n💵 +{salaire:,} € | +10 XP")

async def sleep(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if est_banni(uid): return

    reste = check_cooldown(uid, "sleep", 30)
    if reste > 0:
        await update.message.reply_text(f"⏳ Attends encore {reste}s.")
        return

    with db:
        db.execute("UPDATE users SET energy = MIN(energy + 40, 100) WHERE id = ?", (uid,))
    await update.message.reply_text("💤 Sieste effectuée. Énergie +40 !")

async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛒 *Boutique Générale*\n\n• `/gilet` - Gilet pare-balles : 40 000 €", parse_mode="Markdown")

async def gilet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if est_banni(uid): return
    p = get_player(update.effective_user)
    prix = 40000
    if p["shield"] > 0:
        await update.message.reply_text("🛡 Tu possèdes déjà un gilet pare-balles.")
        return
    if not remove_cash(uid, prix):
        await update.message.reply_text(f"❌ Le gilet coûte {prix:,} € en cash.")
        return
    
    with db:
        db.execute("UPDATE users SET shield=1 WHERE id=?", (uid,))
    log_action(f"Achat gilet pare-balles par {uid}")
    await update.message.reply_text("🛡 Gilet pare-balles acheté et équipé !")

async def diplome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if est_banni(uid): return
    p = get_player(update.effective_user)
    if p["diploma"] != 'Aucun':
        await update.message.reply_text("🎓 Tu as déjà ton diplôme.")
        return
    prix = 80000
    if not remove_cash(uid, prix):
        await update.message.reply_text(f"❌ Le diplôme coûte {prix:,} €.")
        return
    with db:
        db.execute("UPDATE users SET diploma='Diplôme supérieur' WHERE id=?", (uid,))
    log_action(f"Achat diplôme par {uid}")
    await update.message.reply_text("🎓 Diplôme validé avec succès !")


# ==========================
# 7. MARCHÉ NOIR & INVENTAIRE
# ==========================

async def marche_noire(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if est_banni(update.effective_user.id): return
    cur = db.cursor()
    cur.execute("SELECT item, price, stock FROM market")
    items = cur.fetchall()
    txt = "💊 Marché Noir\n\n" + "".join([f"• {i['item']} : {i['price']:,} € (Stock: {i['stock']})\n" for i in items]) + "\nCommandes : `/buyblack <objet> <qte>` | `/sellblack <objet> <qte>`"
    await update.message.reply_text(txt, parse_mode="Markdown")

async def buyblack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if est_banni(uid): return
    if len(context.args) < 2:
        await update.message.reply_text("Utilisation : `/buyblack <nom_objet> <quantité>`", parse_mode="Markdown")
        return
    try:
        qte = int(context.args[-1])
    except ValueError:
        await update.message.reply_text("❌ Quantité invalide.")
        return
    if qte <= 0: return
    item = " ".join(context.args[:-1]).title()
    
    cur = db.cursor()
    cur.execute("SELECT price, stock FROM market WHERE item=?", (item,))
    res = cur.fetchone()
    if not res:
        await update.message.reply_text("❌ Cet objet n'existe pas au marché noir.")
        return
    if res["stock"] < qte:
        await update.message.reply_text("❌ Stock insuffisant.")
        return
        
    prix = res["price"] * qte
    if prix > MAX_MONEY or not remove_cash(uid, prix):
        await update.message.reply_text("❌ Cash insuffisant ou montant invalide.")
        return
        
    with db:
        db.execute("UPDATE market SET stock=stock-? WHERE item=?", (qte, item))
        db.execute("INSERT INTO inventory(user_id, item, amount) VALUES(?,?,?) ON CONFLICT(user_id,item) DO UPDATE SET amount=amount+?", (uid, item, qte, qte))
    log_action(f"Achat marché noir ({qte} {item}) par {uid}")
    await update.message.reply_text(f"💊 Achat réussi de {qte} {item}.")

async def sellblack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if est_banni(uid): return
    if len(context.args) < 2:
        await update.message.reply_text("Utilisation : `/sellblack <nom_objet> <quantité>`", parse_mode="Markdown")
        return
    try:
        qte = int(context.args[-1])
    except ValueError:
        await update.message.reply_text("❌ Quantité invalide.")
        return
    if qte <= 0: return
    item = " ".join(context.args[:-1]).title()
    
    cur = db.cursor()
    cur.execute("SELECT amount FROM inventory WHERE user_id=? AND item=?", (uid, item))
    inv = cur.fetchone()
    if not inv or inv["amount"] < qte:
        await update.message.reply_text("❌ Quantité insuffisante en inventaire.")
        return
    cur.execute("SELECT price FROM market WHERE item=?", (item,))
    mkt = cur.fetchone()
    if not mkt:
        await update.message.reply_text("❌ Objet inconnu.")
        return
        
    gain = int((mkt["price"] * 0.7) * qte)
    
    with db:
        db.execute("UPDATE inventory SET amount=amount-? WHERE user_id=? AND item=?", (qte, uid, item))
        db.execute("DELETE FROM inventory WHERE user_id=? AND item=? AND amount <= 0", (uid, item))
        db.execute("UPDATE users SET cash = cash + ? WHERE id = ?", (gain, uid))
    log_action(f"Vente marché noir ({qte} {item}) par {uid}")
    await update.message.reply_text(f"💵 Vente effectuée pour {gain:,} €.")

async def inventory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if est_banni(uid): return
    cur = db.cursor()
    cur.execute("SELECT item, amount FROM inventory WHERE user_id=? AND amount > 0", (uid,))
    items = cur.fetchall()
    if not items:
        await update.message.reply_text("🎒 Inventaire vide.")
        return
    await update.message.reply_text("🎒 *Ton Inventaire*\n\n" + "".join([f"• {i['item']} : {i['amount']}\n" for i in items]), parse_mode="Markdown")

async def hopital(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if est_banni(uid): return
    p = get_player(update.effective_user)
    if p["health"] >= 100:
        await update.message.reply_text("🏥 Tu es déjà en pleine forme.")
        return
    if not remove_cash(uid, 20000):
        await update.message.reply_text("❌ Soins insuffisants (20 000 € requis).")
        return
    with db:
        db.execute("UPDATE users SET health=100, energy=100 WHERE id=?", (uid,))
    log_action(f"Soins hôpital par {uid}")
    await update.message.reply_text("🏥 Santé et énergie restaurées à 100%.")


# ==========================================
# 8. BOURSE & INVESTISSEMENTS
# ==========================================

async def bourse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if est_banni(update.effective_user.id): return
    cur = db.cursor()
    cur.execute("SELECT symbol, name, price FROM stock_market")
    stocks = cur.fetchall()
    txt = "📈 Bourse\n\n" + "".join([f"• *{s['symbol']}* ({s['name']}) : {s['price']:,} €\n" for s in stocks]) + "\nCommandes : `/invest <SYMBOLE> <parts>` | `/sellstock <SYMBOLE> <parts>`"
    await update.message.reply_text(txt, parse_mode="Markdown")

async def invest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if est_banni(uid): return
    if len(context.args) < 2:
        await update.message.reply_text("Utilisation : `/invest <SYMBOLE> <parts>`", parse_mode="Markdown")
        return
    sym = context.args[0].upper()
    try:
        shares = int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Nombre de parts invalide.")
        return
    if shares <= 0: return
    
    cur = db.cursor()
    cur.execute("SELECT price FROM stock_market WHERE symbol=?", (sym,))
    res = cur.fetchone()
    if not res:
        await update.message.reply_text("❌ Symbole boursier inconnu.")
        return
    cout = res["price"] * shares
    
    if cout > MAX_MONEY or not remove_cash(uid, cout):
        await update.message.reply_text("❌ Cash insuffisant ou montant invalide.")
        return
    with db:
        db.execute("INSERT INTO user_stocks(user_id, symbol, shares) VALUES(?,?,?) ON CONFLICT(user_id,symbol) DO UPDATE SET shares=shares+?", (uid, sym, shares, shares))
    log_action(f"Investissement de {uid} ({shares} parts de {sym})")
    await update.message.reply_text(f"📈 Achat de {shares} parts de {sym}.")

async def sellstock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if est_banni(uid): return
    if len(context.args) < 2:
        await update.message.reply_text("Utilisation : `/sellstock <SYMBOLE> <parts>`", parse_mode="Markdown")
        return
    sym = context.args[0].upper()
    try:
        shares = int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Nombre de parts invalide.")
        return
    if shares <= 0: return
    
    cur = db.cursor()
    cur.execute("SELECT shares FROM user_stocks WHERE user_id=? AND symbol=?", (uid, sym))
    res = cur.fetchone()
    if not res or res["shares"] < shares:
        await update.message.reply_text("❌ Tu n'as pas assez de parts de ce type.")
        return
    cur.execute("SELECT price FROM stock_market WHERE symbol=?", (sym,))
    gain = cur.fetchone()["price"] * shares
    
    with db:
        db.execute("UPDATE user_stocks SET shares=shares-? WHERE user_id=? AND symbol=?", (shares, uid, sym))
        db.execute("DELETE FROM user_stocks WHERE user_id=? AND symbol=? AND shares <= 0", (uid, sym))
        db.execute("UPDATE users SET cash = cash + ? WHERE id = ?", (gain, uid))
    log_action(f"Vente d'actions de {uid} ({shares} parts de {sym})")
    await update.message.reply_text(f"📊 Vente de parts pour {gain:,} €.")

async def portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if est_banni(uid): return
    cur = db.cursor()
    cur.execute("SELECT symbol, shares FROM user_stocks WHERE user_id=?", (uid,))
    stocks = cur.fetchall()
    if not stocks:
        await update.message.reply_text("📊 Portefeuille vide.")
        return
    await update.message.reply_text("📊 *Portefeuille*\n\n" + "".join([f"• {s['symbol']} : {s['shares']} parts\n" for s in stocks]), parse_mode="Markdown")


# ==========================================
# 9. MARIAGE & DIVORCE INTERACTIF
# ==========================================

async def mariage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if est_banni(uid): return
    if len(context.args) != 1:
        await update.message.reply_text("Utilisation : `/mariage <id_joueur>`", parse_mode="Markdown")
        return
    try:
        cible = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID invalide.")
        return
    
    if cible == uid or cible == OWNER_ID:
        await update.message.reply_text("❌ Cible invalide.")
        return

    get_player(update.effective_user)
    
    cur = db.cursor()
    cur.execute("SELECT id FROM users WHERE id=?", (cible,))
    if not cur.fetchone():
        await update.message.reply_text("❌ Ce joueur n'existe pas dans la base.")
        return

    p_exp = get_player(update.effective_user)
    if p_exp["married_to"] is not None:
        await update.message.reply_text("❌ Tu es déjà marié(e).")
        return

    keyboard = [[InlineKeyboardButton("Accepter 💍", callback_data=f"marry_yes_{uid}"), InlineKeyboardButton("Refuser ❌", callback_data=f"marry_no_{uid}")]]
    try:
        await context.bot.send_message(chat_id=cible, text=f"💍 Le joueur `{uid}` te demande en mariage !", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        await update.message.reply_text("💌 Demande envoyée.")
    except Exception:
        await update.message.reply_text("❌ Le joueur cible doit d'abord lancer /start en Message Privé avec le bot.")

async def mariage_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split("_")
    action, uid = data[1], int(data[2])
    cible = query.from_user.id
    
    get_player(query.from_user)

    cur = db.cursor()
    if action == "yes":
        cur.execute("SELECT married_to FROM users WHERE id IN (?, ?)", (uid, cible))
        rows = cur.fetchall()
        if any(row["married_to"] is not None for row in rows):
            await query.edit_message_text("❌ L'un des deux joueurs est déjà marié(e) !")
            return

        with db:
            db.execute("UPDATE users SET married_to=? WHERE id=?", (cible, uid))
            db.execute("UPDATE users SET married_to=? WHERE id=?", (uid, cible))
        log_action(f"Mariage célébré entre {uid} et {cible}")
        await query.edit_message_text("💍 Mariage célébré avec succès 🎉")
    else:
        await query.edit_message_text("❌ Demande refusée.")

async def divorce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if est_banni(uid): return
    p = get_player(update.effective_user)
    conjoint_id = p["married_to"]
    if conjoint_id is None:
        await update.message.reply_text("❌ Tu n'es pas marié(e).")
        return
    with db:
        db.execute("UPDATE users SET married_to=NULL WHERE id=?", (uid,))
        db.execute("UPDATE users SET married_to=NULL WHERE id=?", (conjoint_id,))
    log_action(f"Divorce prononcé entre {uid} et {conjoint_id}")
    await update.message.reply_text("💔 Le divorce a été prononcé.")


# ==========================================
# 10. JEUX & VOLS AVEC PROTECTION PROPRIÉTAIRE
# ==========================================

async def slots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if est_banni(uid): return

    reste = check_cooldown(uid, "slots", 3)
    if reste > 0:
        await update.message.reply_text(f"⏳ Patiente {reste}s.")
        return

    if not context.args:
        await update.message.reply_text("Utilisation : `/slots <mise>`", parse_mode="Markdown")
        return
    try:
        mise = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Mise invalide.")
        return
    if mise <= 0 or mise > MAX_MONEY:
        await update.message.reply_text("❌ Mise invalide.")
        return
    
    if remove_cash(uid, mise):
        gain = mise * 2 if random.randint(1, 100) <= 35 else 0
        if gain > 0:
            add_cash(uid, gain)
            await update.message.reply_text(f"🎰 Jackpot : +{gain:,} €")
        else:
            await update.message.reply_text("🎰 Perdu !")

async def dice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if est_banni(update.effective_user.id): return
    await update.message.reply_dice()

async def steal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if est_banni(uid): return

    reste = check_cooldown(uid, "steal", 10)
    if reste > 0:
        await update.message.reply_text(f"⏳ La police surveille le secteur ({reste}s).")
        return

    if len(context.args) == 1:
        try:
            cible = int(context.args[0])
            if cible == uid:
                await update.message.reply_text("❌ Tu ne peux pas te voler toi-même.")
                return
            
            if cible == OWNER_ID:
                await update.message.reply_text("❌ Impossible de voler le parrain suprême !")
                return
            
            cur = db.cursor()
            cur.execute("SELECT shield, cash FROM users WHERE id=?", (cible,))
            res_target = cur.fetchone()
            if not res_target:
                await update.message.reply_text("❌ Cible introuvable.")
                return
                
            shield, cash_cible = res_target["shield"], res_target["cash"]
            
            if cash_cible <= 0:
                await update.message.reply_text("🥷 La cible n'a pas un sou en poche !")
                return
                
            if shield > 0:
                with db:
                    db.execute("UPDATE users SET shield=0 WHERE id=?", (cible,))
                await update.message.reply_text("🛡 La cible portait un gilet pare-balles ! Vol bloqué.")
                return
                
            reussite = random.randint(1, 100) <= 45
            if reussite:
                gain = min(int(cash_cible * random.uniform(0.05, 0.15)), cash_cible)
                
                with db:
                    db.execute("UPDATE users SET cash = cash - ? WHERE id = ?", (gain, cible))
                    db.execute("UPDATE users SET cash = cash + ? WHERE id = ?", (gain, uid))
                log_action(f"Vol réussi de {uid} sur {cible} pour {gain}€")
                await update.message.reply_text(f"🥷 Vol réussi : +{gain:,} €")
            else:
                add_health(uid, -15)
                await update.message.reply_text("❌ Échec du vol (-15 HP).")
        except ValueError:
            await update.message.reply_text("❌ ID de cible invalide.")
    else:
        await update.message.reply_text("Utilisation : `/steal <id_joueur>`", parse_mode="Markdown")


# ==========================================
# 11. PANEL ADMIN
# ==========================================

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in super_admins and uid not in moderateurs: return
    await update.message.reply_text("👑 PANEL ADMIN\n\nCommandes:\n`/givecash <id> <montant>`\n`/ban <id>`\n`/unban <id>`", parse_mode="Markdown")

async def givecash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in super_admins: return
    if len(context.args) != 2:
        await update.message.reply_text("Utilisation : `/givecash <id_joueur> <montant>`", parse_mode="Markdown")
        return
    try:
        cible, montant = int(context.args[0]), int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Paramètres invalides.")
        return
    
    get_player(cible, name="Inconnu")

    add_cash(cible, montant)
    log_action(f"Admin a donné {montant}€ à {cible}")
    await update.message.reply_text("✅ Cash ajouté par le Super-Admin.")

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in super_admins and uid not in moderateurs: return
    if not context.args:
        await update.message.reply_text("Utilisation : `/ban <id_joueur>`", parse_mode="Markdown")
        return
    try:
        cible = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID invalide.")
        return
        
    if cible == OWNER_ID:
        await update.message.reply_text("❌ Tu ne peux pas bannir le créateur du bot !")
        return

    with db:
        db.execute("INSERT OR IGNORE INTO bans VALUES(?)", (cible,))
    log_action(f"Utilisateur {cible} banni")
    await update.message.reply_text(f"🚫 Utilisateur `{cible}` banni.", parse_mode="Markdown")

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in super_admins: return
    if not context.args:
        await update.message.reply_text("Utilisation : `/unban <id_joueur>`", parse_mode="Markdown")
        return
    try:
        uid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID invalide.")
        return
    with db:
        db.execute("DELETE FROM bans WHERE user_id=?", (uid,))
    log_action(f"Utilisateur {uid} débanni")
    await update.message.reply_text(f"✅ Utilisateur `{uid}` débanni.", parse_mode="Markdown")


# ==========================================
# 12. LANCEMENT DU BOT & FERMETURE PROPRE
# ==========================================

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logging.exception("Exception non gérée :", exc_info=context.error)

app = ApplicationBuilder().token(TOKEN).build()
app.add_error_handler(error_handler)

job_queue = app.job_queue
job_queue.run_repeating(update_stock_market, interval=900, first=10)
job_queue.run_repeating(cleanup_logs_job, interval=86400, first=60)
job_queue.run_repeating(regenerate_energy_job, interval=900, first=300)

handlers = [
    CommandHandler("start", start), CommandHandler("help", help_cmd),
    CommandHandler("me", me), CommandHandler("acc", acc),
    CommandHandler("top", top), CommandHandler("daily", daily),
    CommandHandler("work", work), CommandHandler("sleep", sleep),
    CommandHandler("bank", bank), CommandHandler("deposit", deposit),
    CommandHandler("withdraw", withdraw), CommandHandler("pay", pay),
    CommandHandler("loan", loan), CommandHandler("rembourser", rembourser),
    CommandHandler("metier", metier), CommandHandler("diplome", diplome),
    CommandHandler("shop", shop), CommandHandler("gilet", gilet),
    CommandHandler("marche_noire", marche_noire), CommandHandler("buyblack", buyblack),
    CommandHandler("sellblack", sellblack), CommandHandler("inventory", inventory),
    CommandHandler("hopital", hopital), CommandHandler("bourse", bourse),
    CommandHandler("invest", invest), CommandHandler("sellstock", sellstock),
    CommandHandler("portfolio", portfolio), CommandHandler("mariage", mariage),
    CommandHandler("divorce", divorce),
    CallbackQueryHandler(mariage_callback, pattern="^marry_"),
    CommandHandler("slots", slots), CommandHandler("dice", dice),
    CommandHandler("steal", steal), CommandHandler("admin", admin),
    CommandHandler("givecash", givecash), CommandHandler("ban", ban),
    CommandHandler("unban", unban)
]

for h in handlers: app.add_handler(h)

print("✅ Mafia City est 100% prêt, propre et optimisé pour la production !")

try:
    app.run_polling()
finally:
    db.close()
    print("🔒 Connexion SQLite fermée proprement.")
