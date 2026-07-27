import logging
import random
import time
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler

# --- CONFIGURATION ---
OWNER_ID = 6559674906
TOKEN = "8027243153:AAHPDVZopFBaNWbiEN-kQegV4gHVy2kOBvY"

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- BASE DE DONNÉES EN MÉMOIRE ---
joueurs = {}
entreprises = {}
banned_users = set()
admins = set([OWNER_ID])
etat_tresor = 50000000
caisse_ville = 10000000
elections = {'active': False, 'candidats': [], 'votes': {}, 'maire': None, 'commission': None}
historique_transactions = []

IMMOBILIER_SHOP = {
    'studio': {'nom': '🏡 Studio', 'prix': 5000, 'loyer': 450},
    'appartement': {'nom': '🏢 Appartement', 'prix': 20000, 'loyer': 1800},
    'maison': {'nom': '🏡 Maison', 'prix': 60000, 'loyer': 5400},
    'villa': {'nom': '🏰 Villa de luxe', 'prix': 200000, 'loyer': 18000},
    'immeuble': {'nom': '🏙️ Immeuble', 'prix': 750000, 'loyer': 66000}
}

def get_player(user_id, name="Joueur"):
    if user_id not in joueurs:
        joueurs[user_id] = {
            'name': name,
            'cash': 500000,  # Solde de départ fixé à 500 000$
            'banks': {'Death': 0, 'Life': 0, 'Nova': 0},
            'loans': [],
            'spouse': None,
            'pending_marry': None,
            'family_name': None,
            'children': [],
            'pending_adopt': None,
            'friends': [],
            'pending_friend': None,
            'diplomes': ['Bac'],
            'entreprise': None,
            'parts': {},
            'immobilier': [],
            'items': [],
            'security': 0,
            'in_jail': False,
            'last_work': None,
            'last_daily': None,
            'last_rent': None,
            'work_count': 0
        }
    return joueurs[user_id]

def is_admin(user_id):
    return user_id in admins or user_id == OWNER_ID

def log_trans(txt):
    historique_transactions.append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {txt}")

# --- COMMANDES DE BASE & PROFIL ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    get_player(u.id, u.first_name)
    await update.message.reply_text(
        f"👑 **Bienvenue dans Empire City / Empire Mafia, {u.first_name} !**\n\n"
        f"💰 Un bonus de démarrage de **500 000 $** a été crédité sur ton compte.\n"
        f"Tape /help pour consulter toutes les commandes disponibles.",
        parse_mode="Markdown"
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📜 **Commandes Empire City / Empire Mafia**\n\n"
        "👤 **Profil & Économie**\n"
        "/start — Créer son compte (Bonus: 500 000 $)\n"
        "/me — Voir son profil\n"
        "/acc — Voir son solde\n"
        "/daily — Bonus quotidien\n"
        "/work — Travailler (Cooldown 5h)\n"
        "/pay @user montant — Envoyer de l'argent\n"
        "/richlist — Top 10 des plus riches\n"
        "/leaderboard — Classement des familles\n"
        "/topactif — Top 15 joueurs actifs\n\n"

        "🏦 **Banque & Prêts**\n"
        "/bank — Liste des banques\n"
        "/openbank nom — Ouvrir un compte (Death, Life, Nova)\n"
        "/depositbank montant banque — Déposer de l'argent\n"
        "/withdrawbank montant banque — Retirer de l'argent\n"
        "/balancebank — Afficher les soldes bancaires\n"
        "/loanbank montant — Prêt bancaire\n"
        "/repaybank montant — Rembourser prêt\n"
        "/loansbank — Prêts en cours\n\n"

        "🏠 **Immobilier & Loyers**\n"
        "/immobilier — Marché immobilier interactif avec boutons\n"
        "/loyer — Récolter les loyers des biens possédés\n\n"

        "👨‍👩‍👧‍👦 **Famille & Social**\n"
        "/marry @user — Demande en mariage\n"
        "/acceptmarry — Accepter le mariage\n"
        "/divorce — Divorcer\n"
        "/adopt @user — Proposer l'adoption\n"
        "/acceptadopt — Accepter l'adoption\n"
        "/disown @user — Désavouer\n"
        "/friend @user — Demande d'ami\n"
        "/acceptfriend — Accepter une demande d'ami\n"
        "/unfriend @user — Retirer un ami\n"
        "/setfamilyname nom — Nom de famille\n"
        "/leave — Quitter sa famille\n"
        "/tree — Arbre généalogique\n\n"

        "🎓 **Éducation**\n"
        "/diplome — Passer ou voir ses diplômes\n\n"

        "🏢 **Entreprises & Parts**\n"
        "/creerboite nom secteur ville — Créer une boîte (50M$)\n"
        "/listeboites — Toutes les entreprises\n"
        "/infoboite nom — Infos entreprise\n"
        "/monentreprise — Ma boîte\n"
        "/postuler nom — Postuler dans une boîte\n"
        "/demissionner — Démissionner\n"
        "/recruter @user — Recruter un employé\n"
        "/licencier @user — Licencier un employé\n"
        "/parts — Répartition des parts\n"
        "/mesparts — Mes parts d'entreprises\n"
        "/acheterparts nom nombre — Acheter des parts\n"
        "/vendreparts nom nombre — Vendre des parts\n\n"

        "🎰 **Casino Solo & PvP**\n"
        "/slots montant | /roulette montant | /mines montant | /crash montant\n"
        "/apple montant | /roue montant | /rebet — Rejouer dernier pari\n"
        "/blackjack montant | /cockfight montant | /ppc choix montant | /lancer montant\n\n"

        "🔫 **Crime & Police**\n"
        "/steal @user | /police @user | /bail | /juge | /security niveau\n"
        "/bid montant | /myitems | /sellitem | /shopitems | /buyitem | /open\n\n"
        "👑 **/owner** — Panel Administrateur Owner"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    p = get_player(u.id, u.first_name)
    total_bank = sum(p['banks'].values())
    msg = (
        f"👤 **Profil de {u.first_name} — Empire City**\n\n"
        f"💵 **Cash :** {p['cash']:,} $\n"
        f"🏦 **Total Banque :** {total_bank:,} $\n"
        f"💍 **Partenaire :** {p['spouse'] if p['spouse'] else 'Célibataire'}\n"
        f"🏰 **Nom de Famille :** {p['family_name'] if p['family_name'] else 'Aucun'}\n"
        f"🎓 **Diplômes :** {', '.join(p['diplomes']) if p['diplomes'] else 'Aucun'}\n"
        f"🏢 **Entreprise :** {p['entreprise'] if p['entreprise'] else 'Aucune'}\n"
        f"🏠 **Biens Immobiliers :** {len(p['immobilier'])}\n"
        f"🛡️ **Niveau de Sécurité :** {p['security']}"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def acc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    await update.message.reply_text(f"💰 **Portefeuille actuel :** {p['cash']:,} $", parse_mode="Markdown")

# --- SYSTÈME WORK (TRAVAIL AVEC COOLDOWN DE 5 HEURES) ---

async def work(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    p = get_player(u.id, u.first_name)
    now = datetime.now()

    if p['last_work']:
        delta = now - p['last_work']
        if delta < timedelta(hours=5):
            remaining = timedelta(hours=5) - delta
            hours, remainder = divmod(remaining.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            await update.message.reply_text(
                f"⏳ **Tu es épuisé par le travail !**\n\n"
                f"Tu dois attendre encore **{hours}h {minutes}m {seconds}s** avant de pouvoir exécuter la commande `/work` à nouveau.",
                parse_mode="Markdown"
            )
            return

    base_pay = random.randint(15000, 35000)
    diplome_multiplier = 1.0 + (len(p['diplomes']) * 0.3)
    total_gagne = int(base_pay * diplome_multiplier)

    p['cash'] += total_gagne
    p['last_work'] = now
    p['work_count'] += 1

    jobs = ["Développeur", "Manager", "Trader", "Directeur Financier", "Consultant", "Avocat"]
    job_actuel = random.choice(jobs)

    msg = (
        f"🛠️ **RAPPORT DE TRAVAIL — EMPIRE CITY**\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 **Employé :** {u.first_name}\n"
        f"💼 **Poste occupé :** {job_actuel}\n"
        f"💵 **Salaire de base :** {base_pay:,} $\n"
        f"🎓 **Bonus Diplômes ({len(p['diplomes'])}) :** +{int((diplome_multiplier-1)*100)}%\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 **Revenu total crédité :** +{total_gagne:,} $\n"
        f"💳 **Nouveau solde cash :** {p['cash']:,} $\n\n"
        f"⏰ Prochaine session disponible dans **5 heures**."
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    now = datetime.now()
    if p['last_daily'] and (now - p['last_daily']) < timedelta(days=1):
        await update.message.reply_text("❌ Tu as déjà récupéré ton bonus quotidien aujourd'hui !")
        return
    bonus = 100000
    p['cash'] += bonus
    p['last_daily'] = now
    await update.message.reply_text(f"🎁 **Bonus Quotidien Récolté !**\n\n💰 **+{bonus:,} $** ajoutés à votre portefeuille.")

# --- IMMOBILIER AVEC BOUTONS INTERACTIFS ---

async def immobilier(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🏡 Studio — 5 000$ (450$/h)", callback_data='buy_studio')],
        [InlineKeyboardButton("🏢 Appartement — 20 000$ (1 800$/h)", callback_data='buy_appartement')],
        [InlineKeyboardButton("🏡 Maison — 60 000$ (5 400$/h)", callback_data='buy_maison')],
        [InlineKeyboardButton("🏰 Villa de luxe — 200 000$ (18 000$/h)", callback_data='buy_villa')],
        [InlineKeyboardButton("🏙️ Immeuble — 750 000$ (66 000$/h)", callback_data='buy_immeuble')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🏠 **Marché immobilier d'Empire City**\n\n"
        "Choisis un bien à acheter :",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    u = query.from_user
    p = get_player(u.id, u.first_name)
    data = query.data

    if data.startswith("buy_"):
        key = data.replace("buy_", "")
        if key in IMMOBILIER_SHOP:
            item = IMMOBILIER_SHOP[key]
            if p['cash'] < item['prix']:
                await query.message.reply_text(f"❌ Solde insuffisant ! Il vous faut **{item['prix']:,} $** pour acheter un **{item['nom']}**.")
            else:
                p['cash'] -= item['prix']
                p['immobilier'].append(item['nom'])
                log_trans(f"{u.first_name} a acheté {item['nom']} pour {item['prix']}$")
                await query.message.reply_text(
                    f"🎉 **Félicitations !** Tu as acheté un **{item['nom']}** pour **{item['prix']:,} $** !\n"
                    f"📈 Revenu généré : **+{item['loyer']:,} $/h**.\n"
                    f"Utilise la commande `/loyer` pour collecter tes revenus.",
                    parse_mode="Markdown"
                )

async def loyer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    p = get_player(u.id, u.first_name)

    if not p['immobilier']:
        await update.message.reply_text("🏠 Vous ne possédez aucun bien immobilier pour le moment.")
        return

    tot_loyer = 0
    lines = []
    for idx, bien in enumerate(p['immobilier'], 1):
        valeur_loyer = 5000
        for item in IMMOBILIER_SHOP.values():
            if item['nom'] in bien:
                valeur_loyer = item['loyer'] * 5
                break
        tot_loyer += valeur_loyer
        lines.append(f"{bien} #{idx} — +{valeur_loyer:,}$")

    p['cash'] += tot_loyer
    details_str = "\n".join(lines[:10])
    
    await update.message.reply_text(
        f"💰 **Loyers collectés : +{tot_loyer:,}$**\n\n"
        f"{details_str}\n\n"
        f"🏦 Versés dans la trésorerie de **{u.first_name}**",
        parse_mode="Markdown"
    )

# --- SYSTEME BANCAIRE ---

async def bank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (
        "🏦 **Banques d'Empire City**\n━━━━━━━━━━━━━━━━━━━━━\n"
        "🥉 **Death** — Taux : 5.0% / 6h\n"
        "💎 **Life** — Taux : 1.0% / 6h\n"
        "🥈 **Nova** — Taux : 2.5% / 6h\n━━━━━━━━━━━━━━━━━━━━━\n"
        "Ouvrir un compte : `/openbank <banque>`"
    )
    await update.message.reply_text(txt, parse_mode="Markdown")

async def openbank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    if not context.args:
        await update.message.reply_text("⚠️ Usage : `/openbank Death` (ou Life, Nova)")
        return
    bname = context.args[0].capitalize()
    if bname in p['banks']:
        await update.message.reply_text(f"✅ Ton compte **{bname}** est actif !")
    else:
        await update.message.reply_text("❌ Choisissez une banque valide : Death, Life, Nova.")

async def depositbank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    try:
        amt = int(context.args[0])
        bname = context.args[1].capitalize()
        if bname not in p['banks']:
            await update.message.reply_text("❌ Banque inexistante.")
            return
        if p['cash'] < amt:
            await update.message.reply_text("❌ Solde cash insuffisant.")
            return
        p['cash'] -= amt
        p['banks'][bname] += amt
        await update.message.reply_text(f"💳 Dépôt réussi de **{amt:,} $** sur **{bname}**.")
    except:
        await update.message.reply_text("⚠️ Usage : `/depositbank <montant> <banque>`")

async def withdrawbank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    try:
        amt = int(context.args[0])
        bname = context.args[1].capitalize()
        if p['banks'].get(bname, 0) < amt:
            await update.message.reply_text("❌ Solde bancaire insuffisant.")
            return
        p['banks'][bname] -= amt
        p['cash'] += amt
        await update.message.reply_text(f"💵 Retrait de **{amt:,} $** de votre compte **{bname}**.")
    except:
        await update.message.reply_text("⚠️ Usage : `/withdrawbank <montant> <banque>`")

async def balancebank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    tot = sum(p['banks'].values())
    msg = (
        f"🏦 **Tes comptes bancaires**\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🥉 **Death** : {p['banks']['Death']:,} $ | Taux: 5.0% / 6h\n"
        f"💎 **Life** : {p['banks']['Life']:,} $ | Taux: 1.0% / 6h\n"
        f"🥈 **Nova** : {p['banks']['Nova']:,} $ | Taux: 2.5% / 6h\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 **Total en banque : {tot:,} $**"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

# --- INTERACTIONS SOCIALES ET ACCEPTATIONS ---

async def acceptfriend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤝 Demande d'ami acceptée avec succès !")

async def acceptmarry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💍 **Félicitations !** Vous êtes désormais mariés !")

async def acceptadopt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👨‍👩‍👧 **Adoption validée !** L'enfant est désormais intégré à la famille.")

# --- ENTREPRISES & CLASSEMENTS ---

async def monentreprise(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    msg = (
        f"🏢 **「 🛒 」 {p['entreprise'] if p['entreprise'] else 'Omzo Corp'}**\n"
        f"✨ **Startup** | ⭐ 3.0/5\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 **VALEUR :** 62.83B $\n"
        f"🏦 **TRÉSORERIE :** 62.83B $\n"
        f"📈 **TON SALAIRE/JOUR :** 0 $/jour\n"
        f"👥 **ÉQUIPE :** 8/200 employés\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"🌐 **TON POSTE :** 👑 PDG"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def richlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sorted_p = sorted(joueurs.items(), key=lambda x: x[1]['cash'] + sum(x[1]['banks'].values()), reverse=True)[:10]
    msg = "🏆 **FORTUNE RANKING — EMPIRE CITY** 🏆\n━━━━━━━━━━━━━━━━━━━━━\n"
    for idx, (uid, p) in enumerate(sorted_p, 1):
        tot = p['cash'] + sum(p['banks'].values())
        msg += f"{idx}. **{p['name']}** ➔ {tot:,} $\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

# --- PANEL OWNER DE EMPIRE CITY ---

async def owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    panel = (
        "👑 **Panel Owner — Empire City**\n\n"
        "💰 `/addmoney id montant` — Ajouter au cash\n"
        "💸 `/removemoney id montant` — Retirer du cash\n"
        "🏦 `/addbanque id montant` — Ajouter en banque\n"
        "🏛️ `/removebanque id montant` — Retirer de la banque\n"
        "🏢 `/addboite nom_entreprise montant` — Ajouter à la trésorerie\n"
        "🏢 `/removeboite nom_entreprise montant` — Retirer de la trésorerie\n"
        "🗡️ `/ban id [raison]` — Bannir un joueur\n"
        "✅ `/unban id` — Débannir un joueur\n"
        "📋 `/listeban [page]` — Liste des joueurs bannis\n"
        "🏢 `/dissoudre nom_entreprise` — Dissoudre une entreprise\n"
        "👑 `/forcenommer nom_entreprise poste` — Forcer nomination\n"
        "🎓 `/setdiplome id secteur palier` — Accorder un diplôme\n"
        "🎓 `/retirerdiplome id secteur palier` — Retirer un diplôme\n"
        "🔄 `/resetrecrutement nom_entreprise` — Lever le cooldown\n"
        "🏛️ `/etatresor` — Voir le solde du fonds État\n"
        "💸 `/utiliserimpots id_ou_pseudo montant [raison]` — Dépenser le fonds État\n"
        "🔓 `/debannirtous` — Débannir tous les joueurs d'un coup\n\n"

        "🏛️ ***Mairie de EMPIRE CITY***\n"
        "🏛️ `/villescaisses` — Voir la caisse municipale\n"
        "💰 `/addcaisseville montant` — Ajouter à la caisse municipale\n"
        "💸 `/removecaisseville montant` — Retirer de la caisse municipale\n"
        "📥 `/ouvrirelection` — Ouvrir une élection municipale (48h)\n"
        "🗳️ `/cloturerelection` — Clôturer le vote\n"
        "👑 `/trancherelection id_ou_pseudo` — Désigner le maire élu\n"
        "📊 `/votesmaire` — Voir le détail des votes\n"
        "⛔ `/revoquermaire` — Révoquer le maire en poste\n"
        "📣 `/lancervote @c1 @c2 [...]` — Poster le vote à boutons\n"
        "👤 `/nommercommission id_ou_pseudo` — Nommer le président\n"
        "🚫 `/retirercandidat id_ou_pseudo` — Retirer un joueur de l'élection\n\n"

        "📈 ***Économie de masse (tous les joueurs)***\n"
        "💰 `/addmoneyall montant` — Ajouter au solde de tous\n"
        "💸 `/removemoneyall montant` — Retirer du solde de tous\n"
        "🏦 `/addbanqueall montant` — Ajouter en banque à tous\n"
        "🏛️ `/removebanqueall montant` — Retirer en banque à tous\n"
        "🔄 `/resetmoneyall [montant]` — Fixer le solde de tous\n"
        "🔄 `/resetbanqueall [montant]` — Fixer la banque de tous\n"
        "📊 `/fixparts nom_entreprise` — Normaliser les parts à 100%\n\n"

        "👤 ***Gestion des administrateurs***\n"
        "👥 `/setadmin id` — Nommer un admin\n"
        "❌ `/unsetadmin id` — Retirer un admin\n"
        "📋 `/listadmins` — Liste des admins\n\n"

        "👥 ***Gestion des joueurs***\n"
        "📜 `/listejoueurs [page]` — Liste tous les joueurs\n"
        "🎓 `/listediplomes [page]` — Liste des diplômes\n"
        "🔍 `/recherchejoueur <nom>` — Rechercher un joueur\n\n"

        "📜 ***Historique & Surveillance***\n"
        "📜 `/historique [nb|tout]` — Dernières transactions\n"
        "👤 `/histojoueur id [nb]` — Transactions d'un joueur\n"
        "🐳 `/baleines [nb]` — Joueurs les plus riches"
    )
    await update.message.reply_text(panel, parse_mode="Markdown")

# LOGIQUE DES COMMANDES DU PANEL OWNER

async def addmoney(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    try:
        uid, amt = int(context.args[0]), int(context.args[1])
        p = get_player(uid)
        p['cash'] += amt
        log_trans(f"Admin a ajouté {amt}$ au cash de {uid}")
        await update.message.reply_text(f"✅ **+{amt:,} $** ajoutés au joueur `{uid}`.", parse_mode="Markdown")
    except: await update.message.reply_text("Usage : `/addmoney <id> <montant>`", parse_mode="Markdown")

async def removemoney(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    try:
        uid, amt = int(context.args[0]), int(context.args[1])
        p = get_player(uid)
        p['cash'] = max(0, p['cash'] - amt)
        log_trans(f"Admin a retiré {amt}$ au cash de {uid}")
        await update.message.reply_text(f"✅ **-{amt:,} $** retirés au joueur `{uid}`.", parse_mode="Markdown")
    except: await update.message.reply_text("Usage : `/removemoney <id> <montant>`", parse_mode="Markdown")

async def addmoneyall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    try:
        amt = int(context.args[0])
        for p in joueurs.values(): p['cash'] += amt
        log_trans(f"Admin a ajouté {amt}$ à TOUS les joueurs")
        await update.message.reply_text(f"✅ **+{amt:,} $** ajoutés au cash de TOUS les joueurs !", parse_mode="Markdown")
    except: await update.message.reply_text("Usage : `/addmoneyall <montant>`", parse_mode="Markdown")

async def removemoneyall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    try:
        amt = int(context.args[0])
        for p in joueurs.values(): p['cash'] = max(0, p['cash'] - amt)
        log_trans(f"Admin a retiré {amt}$ à TOUS les joueurs")
        await update.message.reply_text(f"✅ **-{amt:,} $** retirés du cash de TOUS les joueurs !", parse_mode="Markdown")
    except: await update.message.reply_text("Usage : `/removemoneyall <montant>`", parse_mode="Markdown")

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    try:
        uid = int(context.args[0])
        banned_users.add(uid)
        log_trans(f"Joueur {uid} banni")
        await update.message.reply_text(f"🚫 **Joueur {uid} banni avec succès.**", parse_mode="Markdown")
    except: await update.message.reply_text("Usage : `/ban <id>`", parse_mode="Markdown")

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    try:
        uid = int(context.args[0])
        banned_users.discard(uid)
        log_trans(f"Joueur {uid} débanni")
        await update.message.reply_text(f"✅ **Joueur {uid} débanni avec succès.**", parse_mode="Markdown")
    except: await update.message.reply_text("Usage : `/unban <id>`", parse_mode="Markdown")

async def listeban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    await update.message.reply_text(f"📋 **Joueurs bannis :** {list(banned_users)}")

async def debannirtous(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    banned_users.clear()
    log_trans("Tous les joueurs ont été débannis")
    await update.message.reply_text("🔓 **Tous les joueurs d'Empire City ont été débannis !**")

async def villescaisses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    await update.message.reply_text(f"🏛️ **Caisse Municipale Empire City :** {caisse_ville:,} $")

async def etatresor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    await update.message.reply_text(f"🏛️ **Fonds d'État (Trésor Public) :** {etat_tresor:,} $")

async def baleines(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    sorted_p = sorted(joueurs.items(), key=lambda x: x[1]['cash'] + sum(x[1]['banks'].values()), reverse=True)[:5]
    txt = "🐳 **TOP 5 BALEINES DE EMPIRE CITY**\n━━━━━━━━━━━━━━━━━━━━━\n"
    for idx, (uid, p) in enumerate(sorted_p, 1):
        txt += f"{idx}. ID `{uid}` ({p['name']}) ➔ {p['cash'] + sum(p['banks'].values()):,} $\n"
    await update.message.reply_text(txt, parse_mode="Markdown")

async def historique(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    logs = historique_transactions[-15:]
    msg = "📜 **Dernières Transactions Empire City**\n━━━━━━━━━━━━━━━━━━━━━\n" + "\n".join(logs) if logs else "Aucun historique."
    await update.message.reply_text(msg)

# --- PROGRAMME PRINCIPAL ---

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()

    # Handlers Utilisateurs & Économie
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("me", me))
    app.add_handler(CommandHandler("acc", acc))
    app.add_handler(CommandHandler("work", work))
    app.add_handler(CommandHandler("daily", daily))

    # Immobilier & Loyers
    app.add_handler(CommandHandler("immobilier", immobilier))
    app.add_handler(CommandHandler("loyer", loyer))
    app.add_handler(CallbackQueryHandler(button_click))

    # Banque
    app.add_handler(CommandHandler("bank", bank))
    app.add_handler(CommandHandler("openbank", openbank))
    app.add_handler(CommandHandler("depositbank", depositbank))
    app.add_handler(CommandHandler("withdrawbank", withdrawbank))
    app.add_handler(CommandHandler("balancebank", balancebank))

    # Socials
    app.add_handler(CommandHandler("acceptfriend", acceptfriend))
    app.add_handler(CommandHandler("acceptmarry", acceptmarry))
    app.add_handler(CommandHandler("acceptadopt", acceptadopt))

    # Entreprises & Top
    app.add_handler(CommandHandler("monentreprise", monentreprise))
    app.add_handler(CommandHandler("richlist", richlist))

    # Panel Admin / Owner Empire City
    app.add_handler(CommandHandler("owner", owner))
    app.add_handler(CommandHandler("addmoney", addmoney))
    app.add_handler(CommandHandler("removemoney", removemoney))
    app.add_handler(CommandHandler("addmoneyall", addmoneyall))
    app.add_handler(CommandHandler("removemoneyall", removemoneyall))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("unban", unban))
    app.add_handler(CommandHandler("listeban", listeban))
    app.add_handler(CommandHandler("debannirtous", debannirtous))
    app.add_handler(CommandHandler("villescaisses", villescaisses))
    app.add_handler(CommandHandler("etatresor", etatresor))
    app.add_handler(CommandHandler("baleines", baleines))
    app.add_handler(CommandHandler("historique", historique))

    print("Bot Empire City / Empire Mafia démarré avec succès !")
    app.run_polling()
