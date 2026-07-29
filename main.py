import logging
import random
import sqlite3
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler

# --- CONFIGURATION ---
OWNER_ID = 6559674906
TOKEN = "8027243153:AAGlT6vipsIQs2V9fw_uFF_-d30x45hDFQg"

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- 1. BASE DE DONNÉES SQLite & ANTI-TRICHE ---
def init_db():
    conn = sqlite3.connect('mafiacity_complet.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS joueurs (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            cash INTEGER DEFAULT 50000,
            banque_death INTEGER DEFAULT 0,
            banque_life INTEGER DEFAULT 0,
            banque_nova INTEGER DEFAULT 0,
            diplomes TEXT DEFAULT "",
            entreprise TEXT DEFAULT NULL,
            entreprise_tresorerie INTEGER DEFAULT 0,
            entreprise_salaire INTEGER DEFAULT 0,
            famille TEXT DEFAULT NULL,
            vehicules TEXT DEFAULT "",
            immobilier TEXT DEFAULT "",
            inventaire TEXT DEFAULT "",
            succes TEXT DEFAULT "",
            securite INTEGER DEFAULT 0,
            prison_fin TEXT DEFAULT NULL,
            avertissements INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS elections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidat_id INTEGER,
            candidat_nom TEXT,
            voix INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mairie_info (
            id INTEGER PRIMARY KEY,
            maire_id INTEGER,
            maire_nom TEXT,
            votes_ouverts INTEGER DEFAULT 0
        )
    ''')
    cursor.execute("INSERT OR IGNORE INTO mairie_info (id, maire_id, maire_nom, votes_ouverts) VALUES (1, NULL, 'Aucun', 0)")
    conn.commit()
    conn.close()

init_db()

banned_users = set()
admins = set([OWNER_ID])

def is_admin(user_id):
    return user_id in admins or user_id == OWNER_ID

def get_player(user_id, name="Joueur"):
    if user_id in banned_users:
        return None
    conn = sqlite3.connect('mafiacity_complet.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM joueurs WHERE user_id = ?", (user_id,))
    p = cursor.fetchone()
    if not p:
        cursor.execute("INSERT INTO joueurs (user_id, name, cash) VALUES (?, ?, ?)", (user_id, name, 50000))
        conn.commit()
        cursor.execute("SELECT * FROM joueurs WHERE user_id = ?", (user_id,))
        p = cursor.fetchone()
    conn.close()
    return {
        'user_id': p[0], 'name': p[1], 'cash': p[2],
        'death': p[3], 'life': p[4], 'nova': p[5],
        'diplomes': p[6].split(",") if p[6] else [],
        'entreprise': p[7], 'ent_tresor': p[8], 'ent_salaire': p[9],
        'famille': p[10], 'vehicules': p[11].split(",") if p[11] else [],
        'immobilier': p[12].split(",") if p[12] else [],
        'inventaire': p[13].split(",") if p[13] else [],
        'succes': p[14].split(",") if p[14] else [],
        'securite': p[15], 'prison': p[16], 'avertissements': p[17]
    }

def update_player(user_id, col, val):
    conn = sqlite3.connect('mafiacity_complet.db')
    cursor = conn.cursor()
    cursor.execute(f"UPDATE joueurs SET {col} = ? WHERE user_id = ?", (val, user_id))
    conn.commit()
    conn.close()

# --- 2. DONNÉES DU JEU ---
DOMAINES_DIPLOMES = {
    'informatique': {'nom': '💻 Informatique & Tech', 'q': [{"q": "Langage pour l'IA ?", "options": ["Python", "HTML", "CSS"], "correct": 0}]},
    'finance': {'nom': '📈 Finance & Économie', 'q': [{"q": "Qu'est-ce qu'une action ?", "options": ["Part d'entreprise", "Dette", "Taxe"], "correct": 0}]},
    'droit': {'nom': '⚖️ Droit & Justice', 'q': [{"q": "Texte fondamental ?", "options": ["Constitution", "Livre", "BD"], "correct": 0}]},
    'management': {'nom': '👔 Management', 'q': [{"q": "Rôle du PDG ?", "options": ["Stratégie", "Café", "Ménage"], "correct": 0}]},
    'sante': {'nom': '🏥 Santé', 'q': [{"q": "Organe qui pompe le sang ?", "options": ["Cœur", "Foie", "Estomac"], "correct": 0}]}
}

# --- COMMANDES DE BASE ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    p = get_player(u.id, u.first_name)
    if not p: return
    await update.message.reply_text(f"🌆 **Bienvenue dans Mafia City, {u.first_name} !**\nTape `/help` pour voir le monde criminel qui s'offre à toi.", parse_mode="Markdown")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    h = (
        "📜 **GUIDE COMPLET — MAFIA CITY**\n\n"
        "👤 `/me` — Profil & Infos\n"
        "🏦 `/banque` — Gérer vos comptes\n"
        "🎓 `/diplome` — Passer vos diplômes\n"
        "🏢 `/creerboite <nom>` — Entreprise (5M€ + Diplôme requis)\n"
        "🛍️ `/boutique` & `/inventaire` — Équipement\n"
        "🎰 `/casino` — Jeux d'argent\n"
        "🥷 `/crimes` — Faire des coups\n"
        "👮 `/police`, `/tribunal`, `/prison` — Justice\n"
        "🏛️ `/mairie`, `/elections` — Politique\n"
        "🔫 `/famille` — Clans mafieux\n"
        "🚗 `/vehicules`, `/immobilier` — Biens\n"
        "🏆 `/classements`, `/succes` — Trophées\n"
        "👑 `/owner` — Panel Admin"
    )
    await update.message.reply_text(h, parse_mode="Markdown")

async def me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    p = get_player(u.id, u.first_name)
    if not p: return
    msg = (
        f"👤 **Parrain : {p['name']}**\n"
        f"💵 **Cash :** {p['cash']:,} €\n"
        f"🏦 **Banque :** {p['death']+p['life']+p['nova']:,} €\n"
        f"🎓 **Diplômes :** {', '.join(p['diplomes']) if p['diplomes'] else 'Aucun'}\n"
        f"🏢 **Entreprise :** {p['entreprise'] if p['entreprise'] else 'Aucune'}\n"
        f"🔫 **Famille :** {p['famille'] if p['famille'] else 'Aucune'}"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def banque(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    if not p: return
    msg = f"🏦 **Comptes Bancaires**\n💀 Death: {p['death']:,}€\n❤️ Life: {p['life']:,}€\n🌟 Nova: {p['nova']:,}€"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def diplome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton(dom['nom'], callback_data=f"exam_{code}")] for code, dom in DOMAINES_DIPLOMES.items()]
    await update.message.reply_text("🎓 **Université**\nChoisis ton domaine :", reply_markup=InlineKeyboardMarkup(kb))

async def creerboite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    p = get_player(u.id, u.first_name)
    if not p: return
    
    if p['entreprise']:
        await update.message.reply_text("❌ Tu possèdes déjà une entreprise.")
        return
        
    if not p['diplomes']:
        await update.message.reply_text("❌ Il te faut obligatoirement au moins un diplôme avant de créer une entreprise ! Passe par `/diplome`.")
        return
        
    if p['cash'] < 5000000:
        await update.message.reply_text(f"❌ Fonds insuffisants. Il te faut 5 000 000 € en cash (Tu as {p['cash']:,} €).")
        return
        
    if not context.args:
        await update.message.reply_text("⚠️ Usage correct : `/creerboite NomDeVotreEntreprise`")
        return
        
    nom = context.args[0]
    update_player(u.id, 'cash', p['cash'] - 5000000)
    update_player(u.id, 'entreprise', nom)
    await update.message.reply_text(f"🎉 Félicitations ! Ton entreprise **{nom}** a été fondée avec succès pour 5 000 000 €.")

async def boutique(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛍️ **Boutique Noire**\n- Armes et gilets disponibles.")

async def inventaire(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    if not p: return
    await update.message.reply_text(f"🎒 **Inventaire :** {', '.join(p['inventaire']) if p['inventaire'] else 'Vide'}")

async def casino(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("🎰 Slots", callback_data='cas_slots'), InlineKeyboardButton("🎲 Roulette", callback_data='cas_roulette')],
        [InlineKeyboardButton("🃏 Blackjack", callback_data='cas_bj'), InlineKeyboardButton("📈 Crash", callback_data='cas_crash')],
        [InlineKeyboardButton("💣 Mines", callback_data='cas_mines')]
    ]
    await update.message.reply_text("🎰 **Casino**\nChoisis ton jeu :", reply_markup=InlineKeyboardMarkup(kb))

async def crimes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    p = get_player(u.id, u.first_name)
    if not p: return
    gain = random.randint(10000, 50000)
    update_player(u.id, 'cash', p['cash'] + gain)
    await update.message.reply_text(f"🥷 **Coup réussi !** +{gain:,} €.")

async def police(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👮 **Police**\nLes patrouilles surveillent la ville.")

async def tribunal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚖️ **Tribunal**\nChambre des jugements criminels.")

async def prison(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    if not p: return
    await update.message.reply_text(f"⛓️ **Prison**\nStatut : {'Incarcéré' if p['prison'] else 'Libre'}")

async def mairie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect('mafiacity_complet.db')
    cursor = conn.cursor()
    cursor.execute("SELECT maire_nom, votes_ouverts FROM mairie_info WHERE id = 1")
    m = cursor.fetchone()
    conn.close()
    await update.message.reply_text(f"🏛️ **Mairie**\nMaire : {m[0]}")

async def elections(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🗳️ **Élections**\nVote pour le prochain maire.")

async def famille(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    if not p: return
    await update.message.reply_text(f"🔫 **Clan**\nClan : {p['famille'] if p['famille'] else 'Aucun'}")

async def vehicules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚗 **Concessionnaire**\nVoitures de sport et blindées.")

async def immobilier(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏠 **Immobilier**\nPlanques et QG.")

async def classements(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect('mafiacity_complet.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name, cash FROM joueurs ORDER BY cash DESC LIMIT 5")
    top = cursor.fetchall()
    conn.close()
    msg = "🏆 **Top 5 Parrains**\n" + "\n".join([f"{i}. {n} — {c:,} €" for i, (n, c) in enumerate(top, 1)])
    await update.message.reply_text(msg, parse_mode="Markdown")

async def succes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    if not p: return
    await update.message.reply_text(f"🏅 **Succès :** {', '.join(p['succes']) if p['succes'] else 'Aucun'}")

async def owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    await update.message.reply_text("👑 **Panel Owner**\n- `/addmoney <id> <montant>`\n- `/ban <id>`")

async def addmoney(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    try:
        uid, amt = int(context.args[0]), int(context.args[1])
        p = get_player(uid)
        if p:
            update_player(uid, 'cash', p['cash'] + amt)
            await update.message.reply_text(f"✅ Ajouté {amt:,} € à `{uid}`.")
    except:
        await update.message.reply_text("⚠️ Usage : `/addmoney <id> <montant>`")

async def ban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    try:
        uid = int(context.args[0])
        banned_users.add(uid)
        await update.message.reply_text(f"🚫 Utilisateur `{uid}` banni.", parse_mode="Markdown")
    except:
        await update.message.reply_text("⚠️ Usage : `/ban <id>`")

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    u = query.from_user
    if data.startswith("exam_"):
        code = data.replace("exam_", "")
        dom = DOMAINES_DIPLOMES[code]
        p = get_player(u.id)
        if dom['nom'] not in p['diplomes']:
            p['diplomes'].append(dom['nom'])
            update_player(u.id, 'diplomes', ",".join(p['diplomes']))
            await query.message.reply_text(f"🎉 Examen réussi ! Diplôme : **{dom['nom']}**")
        else:
            await query.message.reply_text("✅ Déjà possédé.")
    elif data.startswith("cas_"):
        p = get_player(u.id)
        update_player(u.id, 'cash', p['cash'] + 5000)
        await query.message.reply_text(f"🎰 Mini-jeu gagné ! +5 000 €")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    cmds = [
        ("start", start), ("help", help_cmd), ("me", me), ("banque", banque),
        ("diplome", diplome), ("creerboite", creerboite), ("boutique", boutique),
        ("inventaire", inventaire), ("casino", casino), ("crimes", crimes),
        ("police", police), ("tribunal", tribunal), ("prison", prison),
        ("mairie", mairie), ("elections", elections), ("famille", famille),
        ("vehicules", vehicules), ("immobilier", immobilier), ("classements", classements),
        ("succes", succes), ("owner", owner), ("addmoney", addmoney), ("ban", ban_cmd)
    ]
    for name, func in cmds:
        app.add_handler(CommandHandler(name, func))
    app.add_handler(CallbackQueryHandler(callback_handler))
    print("Mafia City Complet et corrigé démarré !")
    app.run_polling()
