import logging
import random
import time
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler

# --- CONFIGURATION ---
OWNER_ID = 6559674906
TOKEN = "8027243153:AAGlT6vipsIQs2V9fw_uFF_-d30x45hDFQg"

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- BASE DE DONNÉES EN MÉMOIRE ---
joueurs = {}
banned_users = set()
admins = set([OWNER_ID])
etat_tresor = 50000000
historique_transactions = []

# --- GESTION DE LA MAIRIE (CONTRÔLE TOTAL PAR L'OWNER) ---
mairie_state = {
    'maire_id': None,       # ID du joueur actuellement maire
    'maire_nom': "Aucun",   # Nom du maire
    'caisse_ville': 1000000000 # Trésorerie de la ville gérable par le maire/owner
}

# --- LES 5 DOMAINES DE DIPLÔMES ET LEURS QUESTIONS ---
DOMAINES_DIPLOMES = {
    'informatique': {
        'nom': '💻 Informatique & Tech',
        'questions': [
            {"q": "Quel langage est principalement utilisé pour l'Intelligence Artificielle ?", "options": ["Python", "HTML", "CSS"], "correct": 0},
            {"q": "Que signifie 'HTML' ?", "options": ["HyperText Markup Language", "High Technical Modern Level", "Home Tool Multi Language"], "correct": 0},
            {"q": "Quel composant est le 'cerveau' de l'ordinateur ?", "options": ["Disque Dur", "Processeur (CPU)", "Carte Graphique"], "correct": 1}
        ]
    },
    'finance': {
        'nom': '📈 Finance & Économie',
        'questions': [
            {"q": "Qu'est-ce qu'une action en bourse ?", "options": ["Une part de propriété d'une entreprise", "Un emprunt bancaire", "Une taxe d'État"], "correct": 0},
            {"q": "Que mesure l'inflation ?", "options": ["La hausse générale des prix", "La vitesse d'Internet", "La croissance de la population"], "correct": 0},
            {"q": "Où s'achètent et se vendent les cryptomonnaies ?", "options": ["Sur une plateforme / exchange", "À la boulangerie", "Au tribunal"], "correct": 0}
        ]
    },
    'droit': {
        'nom': '⚖️ Droit & Justice',
        'questions': [
            {"q": "Quel texte fixe les lois fondamentales d'un pays ?", "options": ["La Constitution", "Un roman policier", "Le manuel de cuisine"], "correct": 0},
            {"q": "Qui prononce le verdict lors d'un procès ?", "options": ["Le Juge", "Le Boulanger", "Le Banquier"], "correct": 0},
            {"q": "Que signifie 'présomption d'innocence' ?", "options": ["On est innocent jusqu'à preuve du contraire", "On est coupable d'office", "Tout le monde ment"], "correct": 0}
        ]
    },
    'management': {
        'nom': '👔 Management & Business',
        'questions': [
            {"q": "Quel est le rôle principal d'un PDG ?", "options": ["Diriger la stratégie de l'entreprise", "Nettoyer les bureaux", "Faire du café"], "correct": 0},
            {"q": "Qu'est-ce que le 'chiffre d'affaires' ?", "options": ["Le total des ventes avant déduction des charges", "Le bénéfice net", "Le salaire du patron"], "correct": 0},
            {"q": "Que gère les Ressources Humaines (RH) ?", "options": ["Le personnel et le recrutement", "La météo", "Les serveurs informatiques"], "correct": 0}
        ]
    },
    'sante': {
        'nom': '🏥 Santé & Médecine',
        'questions': [
            {"q": "Quel organe pompe le sang dans le corps humain ?", "options": ["Le Cœur", "Le Foie", "L'Estomac"], "correct": 0},
            {"q": "Combien de paires de chromosomes possède l'humain en général ?", "options": ["23", "10", "50"], "correct": 0},
            {"q": "Quel professionnel de santé soigne les dents ?", "options": ["Le Dentiste", "L'Ophtalmologue", "Le Cardiologue"], "correct": 0}
        ]
    }
}

def get_player(user_id, name="Joueur"):
    if user_id not in joueurs:
        joueurs[user_id] = {
            'name': name,
            'cash': 50000,
            'banks': {'Death': 0, 'Life': 0, 'Nova': 0},
            'diplomes': [],
            'entreprise': None,
            'immobilier': [],
            'security': 0,
            'last_work': None,
            'last_daily': None,
            'active_exam': None
        }
    else:
        joueurs[user_id]['name'] = name
    return joueurs[user_id]

def is_admin(user_id):
    return user_id in admins or user_id == OWNER_ID

def log_trans(txt):
    historique_transactions.append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {txt}")

# --- COMMANDES DE BASE ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    get_player(u.id, u.first_name)
    await update.message.reply_text(
        f"👑 **Bienvenue dans Empire City, {u.first_name} !**\n\n"
        f"Passe tes diplômes, monte ta boîte et respecte l'autorité suprême de la ville.\n"
        f"Tape /help pour consulter les commandes.",
        parse_mode="Markdown"
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📜 **Commandes Empire City**\n\n"
        "👤 **Profil & Économie**\n"
        "/me — Voir son profil\n"
        "/acc — Voir son solde\n"
        "/work — Travailler\n"
        "/daily — Bonus quotidien\n\n"

        "🎓 **Diplômes**\n"
        "/diplome — Passer un examen dans l'un des 5 domaines\n\n"

        "🏢 **Entreprises & Salaires**\n"
        "/creerboite nom — Créer une boîte (5M€ + Diplôme requis)\n"
        "/monentreprise — Ma boîte\n"
        "/setsalaire montant — Fixer le salaire\n"
        "/versesalaire — Verser le salaire\n\n"

        "🏛️ **Mairie**\n"
        "/mairie — Voir le maire actuel et la caisse de la ville\n\n"

        "👑 **Commandes Owner (Réservé à toi)**\n"
        "/setmaire <user_id> — Nommer directement le maire\n"
        "/owner — Panel d'administration complet"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    p = get_player(u.id, u.first_name)
    total_bank = sum(p['banks'].values())
    ent_nom = p['entreprise']['nom'] if p['entreprise'] else 'Aucune'
    diplomes_str = ", ".join(p['diplomes']) if p['diplomes'] else 'Aucun'

    msg = (
        f"👤 **Profil de {u.first_name}**\n\n"
        f"💵 **Cash :** {p['cash']:,} €\n"
        f"🏦 **Banque :** {total_bank:,} €\n"
        f"🎓 **Diplômes :** {diplomes_str}\n"
        f"🏢 **Entreprise :** {ent_nom}"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def acc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    await update.message.reply_text(f"💰 **Portefeuille actuel :** {p['cash']:,} €", parse_mode="Markdown")

async def work(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    p = get_player(u.id, u.first_name)
    base_pay = random.randint(15000, 35000)
    multiplier = 1.0 + (len(p['diplomes']) * 0.4)
    total_gagne = int(base_pay * multiplier)
    p['cash'] += total_gagne
    await update.message.reply_text(f"🛠️ Travail effectué ! Tu as gagné **+{total_gagne:,} €**.", parse_mode="Markdown")

async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    bonus = 100000
    p['cash'] += bonus
    await update.message.reply_text(f"🎁 **+{bonus:,} €** ajoutés à votre portefeuille.")

# --- SYSTÈME DES DIPLÔMES (QCM) ---

async def diplome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    p = get_player(u.id, u.first_name)

    keyboard = []
    for code, dom in DOMAINES_DIPLOMES.items():
        status = "✅ Obtenu" if dom['nom'] in p['diplomes'] else "❌ À passer"
        keyboard.append([InlineKeyboardButton(f"{dom['nom']} ({status})", callback_data=f"exam_{code}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🎓 **Centre des Examens d'Empire City**\n\n"
        "Choisis un domaine ci-dessous pour passer ton examen :",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# --- SYSTÈME DE LA MAIRIE (CONTRÔLE TOTAL) ---

async def mairie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🏛️ **Hôtel de Ville d'Empire City**\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"👑 **Maire Actuel :** {mairie_state['maire_nom']}\n"
        f"💰 **Caisse de la Ville :** {mairie_state['caisse_ville']:,} €\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 *Le maire est désigné par l'Autorité Suprême (l'Owner).* "
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def setmaire(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Commande réservée au propriétaire suprême.")
        return
    try:
        target_id = int(context.args[0])
        target_player = get_player(target_id)
        
        mairie_state['maire_id'] = target_id
        mairie_state['maire_nom'] = target_player['name']
        
        log_trans(f"L'Owner a nommé {target_player['name']} ({target_id}) comme Maire.")
        await update.message.reply_text(
            f"👑 **Nomination réussie !**\n"
            f"Le joueur **{target_player['name']}** (`{target_id}`) est officiellement le nouveau Maire d'Empire City.",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text("⚠️ **Usage incorrect :** `/setmaire <user_id>`\n*(Assure-toi que le joueur a déjà interagi avec le bot au moins une fois)*", parse_mode="Markdown")

# --- GESTION DES CLICS DE BOUTONS (Examens) ---

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    u = query.from_user
    p = get_player(u.id, u.first_name)
    data = query.data

    if data.startswith("exam_"):
        code_domaine = data.replace("exam_", "")
        dom = DOMAINES_DIPLOMES[code_domaine]

        if dom['nom'] in p['diplomes']:
            await query.message.reply_text(f"✅ Tu possèdes déjà le diplôme en **{dom['nom']}** !")
            return

        p['active_exam'] = {'domaine': code_domaine, 'q_index': 0, 'score': 0}
        await poser_question_examen(query.message, p)

    elif data.startswith("ans_"):
        exam = p.get('active_exam')
        if not exam:
            await query.message.reply_text("❌ Aucun examen en cours.")
            return

        choix_fait = int(data.replace("ans_", ""))
        dom = DOMAINES_DIPLOMES[exam['domaine']]
        question_actuelle = dom['questions'][exam['q_index']]

        if choix_fait == question_actuelle['correct']:
            exam['score'] += 1

        exam['q_index'] += 1

        if exam['q_index'] < len(dom['questions']):
            await poser_question_examen(query.message, p)
        else:
            score_final = exam['score']
            total_questions = len(dom['questions'])
            p['active_exam'] = None

            if score_final >= 2:
                if dom['nom'] not in p['diplomes']:
                    p['diplomes'].append(dom['nom'])
                await query.message.reply_text(
                    f"🎉 **EXAMEN RÉUSSI !**\n"
                    f"Domaine : **{dom['nom']}** | Score : **{score_final}/{total_questions}**\n"
                    f"🎓 Diplôme obtenu !",
                    parse_mode="Markdown"
                )
            else:
                await query.message.reply_text(
                    f"❌ **EXAMEN ÉCHOUÉ...** ({score_final}/{total_questions}). Réessaie avec `/diplome`."
                )

async def poser_question_examen(message, p):
    exam = p['active_exam']
    dom = DOMAINES_DIPLOMES[exam['domaine']]
    q_data = dom['questions'][exam['q_index']]

    keyboard = []
    for idx, option in enumerate(q_data['options']):
        keyboard.append([InlineKeyboardButton(option, callback_data=f"ans_{idx}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await message.edit_text(
        f"📝 **Examen : {dom['nom']}**\n"
        f"Question {exam['q_index'] + 1} / {len(dom['questions'])}\n\n"
        f"❓ *{q_data['q']}*",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# --- ENTREPRISES ---

async def creerboite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    p = get_player(u.id, u.first_name)

    if p['entreprise']:
        await update.message.reply_text("❌ Tu possèdes déjà une entreprise !")
        return

    if not p['diplomes']:
        await update.message.reply_text("🎓 **Refusé !** Tu dois obtenir au moins un diplôme via `/diplome` avant de créer une entreprise.")
        return

    PRIX_CREATION = 5000000
    if p['cash'] < PRIX_CREATION:
        await update.message.reply_text(f"❌ Il te faut **5 000 000 €** en cash. Solde : **{p['cash']:,} €**")
        return

    if not context.args:
        await update.message.reply_text("⚠️ Usage : `/creerboite NomDeTonEntreprise`")
        return

    nom_boite = context.args[0]
    p['cash'] -= PRIX_CREATION
    p['entreprise'] = {'nom': nom_boite, 'tresorerie': 0, 'valeur': 0, 'employes': 0, 'salaire': 0}

    await update.message.reply_text(f"🎉 Entreprise **{nom_boite}** créée pour **5 000 000 €** !")

async def monentreprise(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    ent = p.get('entreprise')
    if not ent:
        await update.message.reply_text("🏢 Tu n'as pas d'entreprise. Utilise `/creerboite <nom>`.")
        return
    msg = f"🏢 **{ent['nom']}**\n💰 Trésorerie : {ent['tresorerie']:,} €\n📈 Salaire fixé : {ent.get('salaire', 0):,} €/jour"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def setsalaire(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    ent = p.get('entreprise')
    if not ent:
        await update.message.reply_text("❌ Tu n'as pas d'entreprise.")
        return
    try:
        montant = int(context.args[0])
        ent['salaire'] = montant
        await update.message.reply_text(f"✅ Salaire journalier fixé à **{montant:,} €**.")
    except:
        await update.message.reply_text("⚠️ Usage : `/setsalaire <montant>`")

async def versesalaire(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    ent = p.get('entreprise')
    if not ent:
        await update.message.reply_text("❌ Tu n'as pas d'entreprise.")
        return
    salaire = ent.get('salaire', 0)
    if ent['tresorerie'] < salaire:
        await update.message.reply_text("❌ Trésorerie insuffisante.")
        return
    ent['tresorerie'] -= salaire
    p['cash'] += salaire
    await update.message.reply_text(f"💸 Versement de **{salaire:,} €** effectué !")

# --- PANEL OWNER ---

async def owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    panel = (
        "👑 **Panel Owner — Contrôle Total**\n\n"
        "🏛️ `/setmaire <id>` — Nommer directement le maire\n"
        "💰 `/addmoney id montant` — Ajouter de l'argent\n"
        "💸 `/removemoney id montant` — Retirer de l'argent\n"
        "🗡️ `/ban id` — Bannir un joueur\n"
        "✅ `/unban id` — Débannir un joueur\n"
        "📜 `/historique` — Voir l'historique des actions"
    )
    await update.message.reply_text(panel, parse_mode="Markdown")

async def addmoney(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    try:
        uid, amt = int(context.args[0]), int(context.args[1])
        p = get_player(uid)
        p['cash'] += amt
        log_trans(f"Admin a ajouté {amt}€ à {uid}")
        await update.message.reply_text(f"✅ **+{amt:,} €** ajoutés.")
    except: await update.message.reply_text("Usage : `/addmoney <id> <montant>`")

async def removemoney(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    try:
        uid, amt = int(context.args[0]), int(context.args[1])
        p = get_player(uid)
        p['cash'] = max(0, p['cash'] - amt)
        log_trans(f"Admin a retiré {amt}€ à {uid}")
        await update.message.reply_text(f"✅ **-{amt:,} €** retirés.")
    except: await update.message.reply_text("Usage : `/removemoney <id> <montant>`")

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    try:
        uid = int(context.args[0])
        banned_users.add(uid)
        await update.message.reply_text(f"🚫 Joueur `{uid}` banni.", parse_mode="Markdown")
    except: await update.message.reply_text("Usage : `/ban <id>`")

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    try:
        uid = int(context.args[0])
        banned_users.discard(uid)
        await update.message.reply_text(f"✅ Joueur `{uid}` débanni.", parse_mode="Markdown")
    except: await update.message.reply_text("Usage : `/unban <id>`")

async def historique(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    logs = historique_transactions[-15:]
    msg = "📜 **Dernières Transactions**\n" + "\n".join(logs) if logs else "Aucun historique."
    await update.message.reply_text(msg)

# --- PROGRAMME PRINCIPAL ---

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("me", me))
    app.add_handler(CommandHandler("acc", acc))
    app.add_handler(CommandHandler("work", work))
    app.add_handler(CommandHandler("daily", daily))

    # Diplômes & Boutons
    app.add_handler(CommandHandler("diplome", diplome))
    app.add_handler(CallbackQueryHandler(button_click))

    # Mairie (Contrôle Owner)
    app.add_handler(CommandHandler("mairie", mairie))
    app.add_handler(CommandHandler("setmaire", setmaire))

    # Entreprises
    app.add_handler(CommandHandler("creerboite", creerboite))
    app.add_handler(CommandHandler("monentreprise", monentreprise))
    app.add_handler(CommandHandler("setsalaire", setsalaire))
    app.add_handler(CommandHandler("versesalaire", versesalaire))

    # Panel Owner
    app.add_handler(CommandHandler("owner", owner))
    app.add_handler(CommandHandler("addmoney", addmoney))
    app.add_handler(CommandHandler("removemoney", removemoney))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("unban", unban))
    app.add_handler(CommandHandler("historique", historique))

    print("Bot Empire City configuré avec contrôle total administrateur !")
    app.run_polling()
