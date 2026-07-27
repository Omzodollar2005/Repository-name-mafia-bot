import logging
import random
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --- CONFIGURATION ---
OWNER_ID = 6559674906
TOKEN = "8027243153:AAGlT6vipsIQs2V9fw_uFF_-d30x45hDFQg"

# --- BASE DE DONNÉES EN MÉMOIRE ---
joueurs = {}
banned_users = set()

# Configuration des logs
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

def get_player(user_id):
    if user_id not in joueurs:
        joueurs[user_id] = {
            'cash': 1000,
            'bank': 0,
            'loan': 0,
            'spouse': None,
            'family_name': None,
            'friends': [],
            'diplome': None,
            'entreprise': None,
            'items': [],
            'security': 0,
            'in_jail': False,
            'messages_count': 0
        }
    return joueurs[user_id]

def is_banned(user_id):
    return user_id in banned_users

# --- COMMANDES JOUEURS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_banned(user_id):
        await update.message.reply_text("❌ Vous êtes banni du jeu.")
        return
    get_player(user_id)
    await update.message.reply_text("👑 Bienvenue dans Empire Mafia Bot ! Tape /help pour voir toutes les commandes.")

async def acc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_banned(user_id): return
    p = get_player(user_id)
    await update.message.reply_text(f"💰 Cash disponible : {p['cash']} $")

async def me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_banned(user_id): return
    p = get_player(user_id)
    profil = (
        f"👤 **Profil de {update.effective_user.first_name}**\n\n"
        f"💵 Cash : {p['cash']} $\n"
        f"🏦 Banque : {p['bank']} $\n"
        f"💍 Marié(e) : {p['spouse'] if p['spouse'] else 'Célibataire'}\n"
        f"🛡️ Sécurité : {p['security']}\n"
        f"🎓 Diplôme : {p['diplome'] if p['diplome'] else 'Aucun'}"
    )
    await update.message.reply_text(profil, parse_mode="Markdown")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_banned(user_id): return
    menu = (
        "📖 **Commandes Empire Mafia**\n\n"
        "👤 **/me** — Voir ton profil complet\n"
        "💰 **/acc** — Voir ton solde de cash\n"
        "🎲 **/mines <montant>** — Jouer aux mines\n"
        "🍎 **/apple <montant>** — Jouer aux pommes\n"
        "👑 **/owner** — Panel du propriétaire (Admin)"
    )
    await update.message.reply_text(menu, parse_mode="Markdown")

# --- JEUX ET MINI-JEUX ---
async def mines(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_banned(user_id): return
    p = get_player(user_id)
    try:
        bet = int(context.args[0])
        if p['cash'] < bet or bet <= 0:
            await update.message.reply_text("⚠️ Cash insuffisant ou montant invalide !")
            return
        if random.random() > 0.4:
            gain = int(bet * 1.8)
            p['cash'] += (gain - bet)
            await update.message.reply_text(f"💣 Pas de mine ! Tu gagnes {gain} $ !")
        else:
            p['cash'] -= bet
            await update.message.reply_text("💣 BOOM ! Tu as sauté sur une mine !")
    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ Utilisation : `/mines <montant>`", parse_mode="Markdown")

async def apple(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_banned(user_id): return
    p = get_player(user_id)
    try:
        bet = int(context.args[0])
        if p['cash'] < bet or bet <= 0:
            await update.message.reply_text("⚠️ Cash insuffisant ou montant invalide !")
            return
        if random.choice([True, False]):
            gain = int(bet * 1.5)
            p['cash'] += (gain - bet)
            await update.message.reply_text(f"🍎 Pomme saine ! Tu gagnes {gain} $ !")
        else:
            p['cash'] -= bet
            await update.message.reply_text("🍏 Pomme empoisonnée ! Tu perds ta mise.")
    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ Utilisation : `/apple <montant>`", parse_mode="Markdown")

# --- PANEL OWNER (ADMIN) ---
async def owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != OWNER_ID:
        await update.message.reply_text("❌ Accès réservé au propriétaire du bot.")
        return

    panel = (
        "👑 **Panel Owner — Empire Mafia**\n\n"
        "💵 **/addmoney <id> <montant>** — Donner du cash\n"
        "🔧 **/setmoney <id> <montant>** — Ajuster le solde\n"
        "🚫 **/ban <id>** — Bannir un joueur\n"
        "✅ **/unban <id>** — Débannir un joueur"
    )
    await update.message.reply_text(panel, parse_mode="Markdown")

async def addmoney(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    try:
        tid = int(context.args[0])
        amt = int(context.args[1])
        p = get_player(tid)
        p['cash'] += amt
        await update.message.reply_text(f"✅ {amt} $ ajoutés au joueur {tid}.")
    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ Utilisation : `/addmoney <id_joueur> <montant>`", parse_mode="Markdown")

async def setmoney(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    try:
        tid = int(context.args[0])
        amt = int(context.args[1])
        p = get_player(tid)
        p['cash'] = amt
        await update.message.reply_text(f"🔧 Solde du joueur {tid} fixé à {amt} $.")
    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ Utilisation : `/setmoney <id_joueur> <montant>`", parse_mode="Markdown")

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    try:
        tid = int(context.args[0])
        banned_users.add(tid)
        await update.message.reply_text(f"🚫 Le joueur {tid} a été banni.")
    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ Utilisation : `/ban <id_joueur>`", parse_mode="Markdown")

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    try:
        tid = int(context.args[0])
        banned_users.discard(tid)
        await update.message.reply_text(f"✅ Le joueur {tid} a été débanni.")
    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ Utilisation : `/unban <id_joueur>`", parse_mode="Markdown")

# --- DÉMARRAGE DU BOT ---
if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()

    # Inscription des commandes
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("acc", acc))
    app.add_handler(CommandHandler("me", me))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("mines", mines))
    app.add_handler(CommandHandler("apple", apple))
    app.add_handler(CommandHandler("owner", owner))
    app.add_handler(CommandHandler("addmoney", addmoney))
    app.add_handler(CommandHandler("setmoney", setmoney))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("unban", unban))

    print("Bot Empire Mafia démarré avec succès !")
    app.run_polling()
