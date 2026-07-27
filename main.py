import random
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --- CONFIGURATION ---
OWNER_ID = 6559674906
TOKEN = "8027243153:AAG9Ya0V_csLuxerm56qdYU4lVMsAgJjzdk"

# --- BASE DE DONNÉES EN MÉMOIRE ---
joueurs = {}

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

# --- MENU HELP COMPLET ---
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    menu = (
        "📖 *Commandes Empire Mafia*\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "👤 *Profil & Économie*\n"
        "/start — Créer son compte\n"
        "/me — Voir son profil\n"
        "/acc — Voir son solde\n"
        "/daily — Bonus quotidien\n"
        "/work — Travailler\n"
        "/pay id montant — Envoyer de l'argent\n"
        "/richlist — Top des plus riches\n"
        "/topactif — Joueurs les plus actifs\n\n"
        "🏦 *Banque*\n"
        "/balancebank — Solde bancaire\n"
        "/depositbank montant — Déposer en banque\n"
        "/withdrawbank montant — Retirer de la banque\n"
        "/loanbank montant — Demander un prêt\n"
        "/repaybank montant — Rembourser un prêt\n"
        "/loansbank — Voir ses prêts\n\n"
        "👨‍👩‍👧 *Famille & Social*\n"
        "/marry id — Proposer un mariage\n"
        "/divorce — Divorcer\n"
        "/setfamilyname nom — Nom de famille\n"
        "/leave — Quitter la famille\n"
        "/friend id — Ajouter un ami\n"
        "/unfriend id — Supprimer un ami\n\n"
        "🎓 *Éducation*\n"
        "/diplome — Liste des diplômes\n"
        "/passerdiplome nom — Passer un diplôme\n\n"
        "🏢 *Entreprises*\n"
        "/creerboite nom — Créer une entreprise (50 000 $)\n"
        "/monentreprise — Ma boîte\n"
        "/demissionner — Démissionner\n\n"
        "🎰 *Casino Solo*\n"
        "/slots montant — Machine à sous\n"
        "/roulette montant — Roulette\n"
        "/mines montant — Jeu des mines\n"
        "/apple montant — Pomme de fortune\n\n"
        "⚔️ *Casino PvP*\n"
        "/blackjack montant — Jeu du Blackjack\n"
        "/ppc choix montant — Pierre-Papier-Ciseaux\n\n"
        "🔫 *Crime*\n"
        "/steal id — Voler un joueur\n"
        "/bail — Payer sa caution de prison\n"
        "/security — Améliorer sa sécurité\n\n"
        "📦 *Boutique & Objets*\n"
        "/shopitems — Voir la boutique\n"
        "/buyitem id — Acheter un objet\n"
        "/myitems — Mes objets\n"
        "/open — Ouvrir un coffre fort\n\n"
        "👑 *Admin*\n"
        "/owner — Panel Owner\n"
    )
    await update.message.reply_text(menu, parse_mode='Markdown')

# --- COMMANDES PROFIL & ÉCONOMIE ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    await update.message.reply_text(f"Bienvenue {update.effective_user.first_name} dans Empire Mafia ! 🏙️\nTape /help pour voir toutes les commandes.")

async def me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    p['messages_count'] += 1
    msg = (
        f"👤 *Profil de {update.effective_user.first_name}* (ID: `{update.effective_user.id}`)\n"
        f"💵 Cash : {p['cash']} $\n"
        f"🏦 Banque : {p['bank']} $\n"
        f"💳 Prêt dû : {p['loan']} $\n"
        f"💍 Statut : {'Marié(e) avec ' + str(p['spouse']) if p['spouse'] else 'Célibataire'}\n"
        f"🏰 Famille : {p['family_name'] or 'Aucune'}\n"
        f"🎓 Diplôme : {p['diplome'] or 'Aucun'}\n"
        f"🏢 Entreprise : {p['entreprise'] or 'Aucune'}\n"
        f"🎒 Objets : {len(p['items'])}\n"
        f"🛡️ Niveau Sécurité : {p['security']}\n"
        f"⛓️ Statut légal : {'En Prison 🔒' if p['in_jail'] else 'Libre 🟢'}"
    )
    await update.message.reply_text(msg, parse_mode='Markdown')

async def acc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    await update.message.reply_text(f"💰 Cash disponible : {p['cash']} $")

async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    p['cash'] += 2000
    await update.message.reply_text("🎁 Bonus quotidien de 2 000 $ récupéré avec succès !")

async def work(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    if p['in_jail']:
        await update.message.reply_text("🔒 Tu es en prison ! Paye ta caution avec `/bail` pour travailler.")
        return
    gain = random.randint(300, 900)
    p['cash'] += gain
    await update.message.reply_text(f"💼 Mission accomplie ! Tu as gagné {gain} $.")

async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    try:
        target_id = int(context.args[0])
        amount = int(context.args[1])
        if p['cash'] < amount or amount <= 0:
            await update.message.reply_text("⚠️ Cash insuffisant !")
            return
        target = get_player(target_id)
        p['cash'] -= amount
        target['cash'] += amount
        await update.message.reply_text(f"💸 Tu as envoyé {amount} $ au joueur `{target_id}`.", parse_mode='Markdown')
    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ Utilisation : `/pay <id_joueur> <montant>`", parse_mode='Markdown')

async def richlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not joueurs:
        await update.message.reply_text("Aucun joueur enregistré pour le moment.")
        return
    classement = sorted(joueurs.items(), key=lambda x: x[1]['cash'] + x[1]['bank'], reverse=True)[:5]
    text = "🏆 *Top 5 des plus riches :*\n"
    for i, (uid, data) in enumerate(classement, 1):
        total = data['cash'] + data['bank']
        text += f"{i}. Joueur `{uid}` : {total} $\n"
    await update.message.reply_text(text, parse_mode='Markdown')

async def topactif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔥 Tu es actuellement le joueur le plus actif de la session !")

# --- COMMANDES BANQUE ---
async def balancebank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    await update.message.reply_text(f"🏦 Solde en banque : {p['bank']} $\n💳 Prêt en cours : {p['loan']} $")

async def depositbank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    try:
        amount = int(context.args[0])
        if p['cash'] >= amount > 0:
            p['cash'] -= amount
            p['bank'] += amount
            await update.message.reply_text(f"🏦 {amount} $ déposés en banque.")
        else:
            await update.message.reply_text("⚠️ Cash insuffisant.")
    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ Utilisation : `/depositbank <montant>`", parse_mode='Markdown')

async def withdrawbank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    try:
        amount = int(context.args[0])
        if p['bank'] >= amount > 0:
            p['bank'] -= amount
            p['cash'] += amount
            await update.message.reply_text(f"🏦 {amount} $ retirés de la banque.")
        else:
            await update.message.reply_text("⚠️ Solde bancaire insuffisant.")
    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ Utilisation : `/withdrawbank <montant>`", parse_mode='Markdown')

async def loanbank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    try:
        amount = int(context.args[0])
        if p['loan'] > 0:
            await update.message.reply_text("⚠️ Tu as déjà un prêt en cours ! Rembourse-le d'abord.")
            return
        if amount > 20000:
            await update.message.reply_text("⚠️ Limite maximale de prêt : 20 000 $.")
            return
        p['loan'] = amount
        p['bank'] += amount
        await update.message.reply_text(f"💳 Prêt de {amount} $ accordé et versé sur ton compte bancaire !")
    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ Utilisation : `/loanbank <montant>`", parse_mode='Markdown')

async def repaybank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    try:
        amount = int(context.args[0])
        if p['cash'] >= amount and p['loan'] > 0:
            payed = min(amount, p['loan'])
            p['cash'] -= payed
            p['loan'] -= payed
            await update.message.reply_text(f"✅ Tu as remboursé {payed} $. Prêt restant : {p['loan']} $.")
        else:
            await update.message.reply_text("⚠️ Pas de prêt en cours ou cash insuffisant.")
    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ Utilisation : `/repaybank <montant>`", parse_mode='Markdown')

async def loansbank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    await update.message.reply_text(f"💳 Prêt en cours à rembourser : {p['loan']} $")

# --- COMMANDES FAMILLE & SOCIAL ---
async def marry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    try:
        target_id = int(context.args[0])
        p['spouse'] = target_id
        await update.message.reply_text(f"💍 Félicitations ! Tu es maintenant marié(e) avec le joueur `{target_id}` !", parse_mode='Markdown')
    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ Utilisation : `/marry <id_joueur>`", parse_mode='Markdown')

async def divorce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    if p['spouse']:
        p['spouse'] = None
        await update.message.reply_text("💔 Tu as divorcé.")
    else:
        await update.message.reply_text("⚠️ Tu n'es pas marié(e).")

async def setfamilyname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    if not context.args:
        await update.message.reply_text("⚠️ Utilisation : `/setfamilyname <nom>`", parse_mode='Markdown')
        return
    name = " ".join(context.args)
    p['family_name'] = name
    await update.message.reply_text(f"🏰 Nom de famille mis à jour : *{name}*", parse_mode='Markdown')

async def leave_family(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    p['family_name'] = None
    await update.message.reply_text("🚪 Tu as quitté ta famille.")

async def friend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    try:
        fid = int(context.args[0])
        if fid not in p['friends']:
            p['friends'].append(fid)
            await update.message.reply_text(f"🤝 Joueur `{fid}` ajouté à tes amis !", parse_mode='Markdown')
        else:
            await update.message.reply_text("⚠️ Ce joueur est déjà ton ami.")
    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ Utilisation : `/friend <id_joueur>`", parse_mode='Markdown')

async def unfriend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    try:
        fid = int(context.args[0])
        if fid in p['friends']:
            p['friends'].remove(fid)
            await update.message.reply_text(f"❌ Joueur `{fid}` retiré de tes amis.", parse_mode='Markdown')
    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ Utilisation : `/unfriend <id_joueur>`", parse_mode='Markdown')

# --- DIPLÔMES & ENTREPRISES ---
async def diplome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎓 *Diplômes disponibles :*\n\n"
        "1. `Management` — 5 000 $\n"
        "2. `Droit` — 10 000 $\n"
        "3. `Finance` — 20 000 $\n\n"
        "Pour passer un diplôme : `/passerdiplome <nom>`",
        parse_mode='Markdown'
    )

async def passerdiplome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    if not context.args:
        await update.message.reply_text("⚠️ Utilisation : `/passerdiplome Management`", parse_mode='Markdown')
        return
    nom = context.args[0].capitalize()
    prix = 5000 if nom == "Management" else 10000 if nom == "Droit" else 20000 if nom == "Finance" else 0
    if prix == 0:
        await update.message.reply_text("⚠️ Diplôme inconnu.")
        return
    if p['cash'] < prix:
        await update.message.reply_text(f"⚠️ Cash insuffisant ! Il faut {prix} $.")
        return
    p['cash'] -= prix
    p['diplome'] = nom
    await update.message.reply_text(f"🎓 Félicitations ! Tu as obtenu le diplôme *{nom}* !", parse_mode='Markdown')

async def creerboite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    if not context.args:
        await update.message.reply_text("⚠️ Utilisation : `/creerboite <nom>`", parse_mode='Markdown')
        return
    nom = " ".join(context.args)
    cout = 50000
    if p['cash'] < cout:
        await update.message.reply_text(f"⚠️ Créer une boîte coûte {cout} $.")
        return
    p['cash'] -= cout
    p['entreprise'] = nom
    await update.message.reply_text(f"🏢 Entreprise *{nom}* créée avec succès !", parse_mode='Markdown')

async def monentreprise(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    if p['entreprise']:
        await update.message.reply_text(f"🏢 *{p['entreprise']}*\nStatut : En activité 🟢", parse_mode='Markdown')
    else:
        await update.message.reply_text("⚠️ Tu n'as pas d'entreprise. Utilise `/creerboite <nom>`.", parse_mode='Markdown')

async def demissionner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    p['entreprise'] = None
    await update.message.reply_text("🏢 Tu as quitté ton entreprise.")

# --- CASINOS & CRIME ---
async def slots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    try:
        bet = int(context.args[0])
        if p['cash'] < bet or bet <= 0:
            await update.message.reply_text("⚠️ Cash insuffisant !")
            return
        symbols = ["🍋", "🍒", "🔔", "💎"]
        res = [random.choice(symbols) for _ in range(3)]
        if res[0] == res[1] == res[2]:
            gain = bet * 5
            p['cash'] += gain
            await update.message.reply_text(f"🎰 | {' '.join(res)} | JACKPOT ! Gagné {gain} $ 🎉")
        else:
            p['cash'] -= bet
            await update.message.reply_text(f"🎰 | {' '.join(res)} | Perdu {bet} $.")
    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ Utilisation : `/slots <montant>`", parse_mode='Markdown')

async def roulette(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    try:
        bet = int(context.args[0])
        if p['cash'] < bet or bet <= 0:
            await update.message.reply_text("⚠️ Cash insuffisant !")
            return
        if random.choice([True, False]):
            p['cash'] += bet
            await update.message.reply_text(f"🔴 Rouge ! Gagné {bet*2} $.")
        else:
            p['cash'] -= bet
            await update.message.reply_text(f"⚫ Noir ! Perdu {bet} $.")
    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ Utilisation : `/roulette <montant>`", parse_mode='Markdown')

async def mines(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    try:
        bet = int(context.args[0])
        if p['cash'] < bet or bet <= 0:
            await update.message.reply_text("⚠️ Cash insuffisant !")
            return
        if random.random() > 0.4:
            gain = int(bet * 1.8)
            p['cash'] += (gain - bet)
            await update.message.reply_text(f"💣 Pas de mine ! Gagné {gain} $ ! 💎")
        else:
            p['cash'] -= bet
            await update.message.reply_text("💣 BOOM ! Tu as sauté sur une mine.")
    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ Utilisation : `/mines <montant>`", parse_mode='Markdown')

async def apple(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    try:
        bet = int(context.args[0])
        if p['cash'] < bet or bet <= 0:
            await update.message.reply_text("⚠️ Cash insuffisant !")
            return
        if random.choice([True, False]):
            gain = int(bet * 1.5)
            p['cash'] += (gain - bet)
            await update.message.reply_text(f"🍎 Pomme saine ! Gagné {gain} $.")
        else:
            p['cash'] -= bet
            await update.message.reply_text("🍏 Pomme empoisonnée ! Perdu.")
    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ Utilisation : `/apple <montant>`", parse_mode='Markdown')

async def blackjack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    try:
        bet = int(context.args[0])
        if p['cash'] < bet or bet <= 0:
            await update.message.reply_text("⚠️ Cash insuffisant !")
            return
        score = random.randint(15, 21)
        croupier = random.randint(15, 21)
        if score > croupier:
            p['cash'] += bet
            await update.message.reply_text(f"🃏 Ton score: {score} vs Croupier: {croupier} | Gagné {bet*2} $ !")
        else:
            p['cash'] -= bet
            await update.message.reply_text(f"🃏 Ton score: {score} vs Croupier: {croupier} | Perdu {bet} $.")
    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ Utilisation : `/blackjack <montant>`", parse_mode='Markdown')

async def ppc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    try:
        choix = context.args[0].lower()
        bet = int(context.args[1])
        if p['cash'] < bet or bet <= 0:
            await update.message.reply_text("⚠️ Cash insuffisant !")
            return
        opts = ["pierre", "papier", "ciseaux"]
        bot_choice = random.choice(opts)
        if choix == bot_choice:
            await update.message.reply_text(f"✂️ Égalité ! Le bot a joué {bot_choice}.")
        elif (choix == "pierre" and bot_choice == "ciseaux") or (choix == "papier" and bot_choice == "pierre") or (choix == "ciseaux" and bot_choice == "papier"):
            p['cash'] += bet
            await update.message.reply_text(f"🎉 Gagné ! Le bot a joué {bot_choice}. Tu gagnes {bet*2} $.")
        else:
            p['cash'] -= bet
            await update.message.reply_text(f"💥 Perdu ! Le bot a joué {bot_choice}.")
    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ Utilisation : `/ppc pierre/papier/ciseaux <montant>`", parse_mode='Markdown')

async def steal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    try:
        target_id = int(context.args[0])
        target = get_player(target_id)
        if random.random() > (0.5 + target['security'] * 0.1):
            stolen = random.randint(100, min(500, max(100, target['cash'])))
            target['cash'] -= stolen
            p['cash'] += stolen
            await update.message.reply_text(f"🥷 Vol réussi ! Tu as dérobé {stolen} $ à `{target_id}`.", parse_mode='Markdown')
        else:
            p['in_jail'] = True
            await update.message.reply_text("🚔 Échec du vol ! La police t'a attrapé. Tu es en prison (Paye ta caution avec `/bail`).")
    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ Utilisation : `/steal <id_joueur>`", parse_mode='Markdown')

async def bail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    if not p['in_jail']:
        await update.message.reply_text("🟢 Tu n'es pas en prison !")
        return
    if p['cash'] < 1000:
        await update.message.reply_text("⚠️ La caution coûte 1 000 $.")
        return
    p['cash'] -= 1000
    p['in_jail'] = False
    await update.message.reply_text("🔓 Caution payée ! Tu es libre.")

async def security(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    cost = (p['security'] + 1) * 2000
    if p['cash'] < cost:
        await update.message.reply_text(f"⚠️ Améliorer la sécurité au niveau {p['security']+1} coûte {cost} $.")
        return
    p['cash'] -= cost
    p['security'] += 1
    await update.message.reply_text(f"🛡️ Sécurité améliorée au niveau {p['security']} !")

# --- BOUTIQUE & OBGETS ---
async def shopitems(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🛍️ *Boutique de la Mafia :*\n\n"
        "1. `1` — Coffre Fort (Prix : 3 000 $)\n"
        "2. `2` — Montre de Luxe (Prix : 10 000 $)\n"
        "3. `3` — Pass VIP (Prix : 50 000 $)\n\n"
        "Pour acheter : `/buyitem <id>`",
    )
    await update.message.reply_text(msg[0], parse_mode='Markdown')

async def buyitem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    try:
        item_id = int(context.args[0])
        items = {1: ("Coffre Fort", 3000), 2: ("Montre de Luxe", 10000), 3: ("Pass VIP", 50000)}
        if item_id not in items:
            await update.message.reply_text("⚠️ Objet inexistant.")
            return
        name, price = items[item_id]
        if p['cash'] < price:
            await update.message.reply_text(f"⚠️ Tu n'as pas {price} $.")
            return
        p['cash'] -= price
        p['items'].append(name)
        await update.message.reply_text(f"📦 Tu as acheté : *{name}* !", parse_mode='Markdown')
    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ Utilisation : `/buyitem <id>`", parse_mode='Markdown')

async def myitems(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    if p['items']:
        await update.message.reply_text(f"🎒 *Tes objets :*\n• " + "\n• ".join(p['items']), parse_mode='Markdown')
    else:
        await update.message.reply_text("🎒 Ton inventaire est vide.")

async def open_box(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_player(update.effective_user.id)
    if "Coffre Fort" in p['items']:
        p['items'].remove("Coffre Fort")
        gain = random.randint(1000, 8000)
        p['cash'] += gain
        await update.message.reply_text(f"🎁 Coffre fort ouvert ! Tu as trouvé {gain} $ dedans !")
    else:
        await update.message.reply_text("⚠️ Tu n'as pas de Coffre Fort dans ton inventaire (Achète-le sur `/shopitems`).")

# --- PANEL OWNER ---
async def owner_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Accès réservé à l'Owner !")
        return
    msg = (
        "👑 *Panel Owner — Empire Mafia*\n\n"
        "💰 `/addmoney id montant` — Donner de l'argent\n"
        "🔨 `/setmoney id montant` — Ajuster le solde"
    )
    await update.message.reply_text(msg, parse_mode='Markdown')

async def addmoney(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    try:
        tid = int(context.args[0])
        amt = int(context.args[1])
        get_player(tid)['cash'] += amt
        await update.message.reply_text(f"✅ {amt} $ ajoutés au joueur `{tid}`.", parse_mode='Markdown')
    except:
        await update.message.reply_text("⚠️ Utilisation : `/addmoney <id> <montant>`")

# --- DÉMARRAGE DU BOT ---
if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()

    handlers = {
        "start": start, "help": help_cmd, "me": me, "acc": acc, "daily": daily, "work": work,
        "pay": pay, "richlist": richlist, "topactif": topactif, "balancebank": balancebank,
        "depositbank": depositbank, "withdrawbank": withdrawbank, "loanbank": loanbank,
        "repaybank": repaybank, "loansbank": loansbank, "marry": marry, "divorce": divorce,
        "setfamilyname": setfamilyname, "leave": leave_family, "friend": friend, "unfriend": unfriend,
        "diplome": diplome, "passerdiplome": passerdiplome, "creerboite": creerboite,
        "monentreprise": monentreprise, "demissionner": demissionner, "slots": slots,
        "roulette": roulette, "mines": mines, "apple": apple, "blackjack": blackjack,
        "ppc": ppc, "steal": steal, "bail": bail, "security": security, "shopitems": shopitems,
        "buyitem": buyitem, "myitems": myitems, "open": open_box, "owner": owner_panel,
        "addmoney": addmoney
    }

    for cmd, func in handlers.items():
        app.add_handler(CommandHandler(cmd, func))

    print("BOT MIS A JOUR V2 OK !")
    app.run_polling() 
