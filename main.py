import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
)

# Configuration des logs
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- STRUCTURES DE DONNÉES SIMULÉES (À relier à ta BDD) ---
users = {}  # user_id: { 'balance': 0, 'bank': {}, 'job': None, 'family': None, ... }
companies = {}  # name: { 'owner': id, 'capital': 0, 'sectors': ..., 'shares': {} }
items_shop = {
    1: {"name": "Coffre mystère", "price": 5000},
    2: {"name": "Armure lourde", "price": 25000},
}


# --- FONCTIONS UTILITAIRES ---
def get_user(user_id):
  if user_id not in users:
    users[user_id] = {
        "balance": 1000,
        "bank": {},
        "spouse": None,
        "family_name": None,
        "items": [],
        "jail": 0,
    }
  return users[user_id]


# ==========================================
# 👤 PROFIL & ÉCONOMIE
# ==========================================


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  user = update.effective_user
  get_user(user.id)
  await update.message.reply_text(
      f"🏙️ Bienvenue à **LifeCity**, {user.first_name} !\nUtilise /me pour voir"
      " ton profil et /acc pour ton solde."
  )


async def me(update: Update, context: ContextTypes.DEFAULT_TYPE):
  u = get_user(update.effective_user.id)
  await update.message.reply_text(
      f"👤 **Profil de {update.effective_user.first_name}**\n"
      f"💰 Liquide : {u['balance']} €\n"
      f"💍 Conjoint : {u['spouse'] or 'Célibataire'}\n"
      f"🏷️ Famille : {u['family_name'] or 'Aucune'}"
  )


async def acc(update: Update, context: ContextTypes.DEFAULT_TYPE):
  u = get_user(update.effective_user.id)
  total_bank = sum(u["bank"].values())
  await update.message.reply_text(
      f"💳 **Solde de compte**\n💵 Espèces : {u['balance']} €\n🏦 Banques :"
      f" {total_bank} €"
  )


async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
  u = get_user(update.effective_user.id)
  u["balance"] += 5000
  await update.message.reply_text(
      "🎁 Bonus quotidien récupéré : +5 000 € !"
  )


async def work(update: Update, context: ContextTypes.DEFAULT_TYPE):
  u = get_user(update.effective_user.id)
  earn = random.randint(500, 2000)
  u["balance"] += earn
  await update.message.reply_text(
      f"💼 Tu as travaillé dur et gagné {earn} €."
  )


async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if not context.args or len(context.args) < 2:
    await update.message.reply_text("Utilisation : /pay @user montant")
    return
  await update.message.reply_text("💸 Transfert effectué avec succès.")


async def richlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text(
      "🏆 **Top 10 des plus riches**\n1. En attente de classement..."
  )


async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text("👑 **Classement royal des familles**")


async def topactif(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text("⚡ **Top 15 des joueurs les plus actifs**")


# ==========================================
# 🏦 BANQUE
# ==========================================


async def bank_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text(
      "🏦 **Banques disponibles à LifeCity**\n- CentralBank\n- NovaBank\n- DeathBank"
  )


async def openbank(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if not context.args:
    await update.message.reply_text("Utilisation : /openbank nom")
    return
  bank_name = context.args[0]
  u = get_user(update.effective_user.id)
  u["bank"][bank_name] = 0
  await update.message.reply_text(f"✅ Compte ouvert chez {bank_name} !")


async def depositbank(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text("💰 Argent déposé en banque.")


async def withdrawbank(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text("💵 Argent retiré de la banque.")


async def balancebank(update: Update, context: ContextTypes.DEFAULT_TYPE):
  u = get_user(update.effective_user.id)
  text = "🏦 **Vos comptes bancaires :**\n"
  for b, amt in u["bank"].items():
    text += f"- {b} : {amt} €\n"
  await update.message.reply_text(text)


async def loanbank(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text("📋 Demande de prêt enregistrée.")


async def repaybank(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text("✅ Prêt remboursé.")


async def loansbank(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text("📊 Vous n'avez aucun prêt en cours.")


# ==========================================
# 👨‍👩‍👧 FAMILLE & SOCIAL
# ==========================================


async def marry(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text(
      "💍 Demande de mariage envoyée à votre partenaire."
  )


async def divorce(update: Update, context: ContextTypes.DEFAULT_TYPE):
  u = get_user(update.effective_user.id)
  u["spouse"] = None
  await update.message.reply_text("💔 Vous êtes désormais divorcé(e).")


async def adopt(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text("👶 Demande d'adoption prise en compte.")


async def disown(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text("❌ Membre désavoué de la famille.")


async def friend(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text("🤝 Demande d'ami envoyée.")


async def unfriend(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text("🚫 Ami retiré.")


async def setfamilyname(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if not context.args:
    await update.message.reply_text("Utilisation : /setfamilyname nom")
    return
  u = get_user(update.effective_user.id)
  u["family_name"] = context.args[0]
  await update.message.reply_text(f"🏷️ Nom de famille défini : {context.args[0]}")


async def leave_family(update: Update, context: ContextTypes.DEFAULT_TYPE):
  u = get_user(update.effective_user.id)
  u["family_name"] = None
  await update.message.reply_text("🚪 Vous avez quitté votre famille.")


async def tree(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text(
      "🌳 **Votre Arbre Généalogique**\n(En construction...)"
  )


# ==========================================
# 🎓 ÉDUCATION
# ==========================================


async def diplome(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if len(context.args) == 0:
    await update.message.reply_text(
        "🎓 **Diplômes disponibles :**\n- Informatique\n- Droit\n- Médecine\n\nFais"
        " `/diplome [nom]` pour passer le test."
    )
  else:
    await update.message.reply_text(
        f"🎓 Félicitations ! Vous avez obtenu le diplôme de"
        f" {context.args[0]}."
    )


# ==========================================
# 🏢 ENTREPRISES & 💰 FINANCES ENTREPRISE
# ==========================================


async def creerboite(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if len(context.args) < 3:
    await update.message.reply_text(
        "Utilisation : /creerboite nom secteur ville (Coût: 50M€)"
    )
    return
  name, sector, city = context.args[0], context.args[1], context.args[2]
  companies[name] = {
      "owner": update.effective_user.id,
      "capital": 50000000,
      "sector": sector,
      "city": city,
  }
  await update.message.reply_text(
      f"🏢 L'entreprise **{name}** ({sector}) a été créée à {city} !"
  )


async def listeboites(update: Update, context: ContextTypes.DEFAULT_TYPE):
  text = "🏢 **Liste des entreprises :**\n"
  for name, data in companies.items():
    text += f"- {name} ({data['sector']}) à {data['city']}\n"
  if not companies:
    text += "Aucune entreprise active pour le moment."
  await update.message.reply_text(text)


async def infoboite(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text("📊 Informations de l'entreprise.")


async def monentreprise(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text("💼 Gestion de votre entreprise.")


async def postuler(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text("📄 Votre candidature a été transmise.")


async def demissionner(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text("🚪 Vous avez démissionné de votre poste.")


async def parts_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text("📈 Répartition des parts de l'entreprise.")


async def versersalaires(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text("💵 Salaires versés aux employés.")


# ==========================================
# 🎰 CASINO SOLO & 🃏 CASINO PVP
# ==========================================


async def slots(update: Update, context: ContextTypes.DEFAULT_TYPE):
  symbols = ["🍒", "🍋", "🍊", "🔔", " 7️⃣"]
  res = [random.choice(symbols) for _ in range(3)]
  await update.message.reply_text(
      f"🎰 Machine à sous\n| {' '.join(res)} |\n"
      + (
          "🎉 Gagné !"
          if res[0] == res[1] == res[2]
          else "😢 Perdu, retente ta chance !"
      )
  )


async def roulette_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text("🎲 La roulette tourne... Numéro 17 (Rouge).")


async def mines(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text(
      "💣 Partie de mines lancée. Évitez les explosions !"
  )


async def crash(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text(
      "📈 Le multiplicateur monte... Crash à 2.45x !"
  )


async def blackjack(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text(
      "🃏 Table de Blackjack ouverte. À vous de jouer !"
  )


async def ppc(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text("✌️ Pierre, Papier, Ciseaux engagé !")


# ==========================================
# 🔫 CRIME & JUSTICE
# ==========================================


async def steal(update: Update, context: ContextTypes.DEFAULT_TYPE):
  success = random.choice([True, False])
  if success:
    await update.message.reply_text(
        "🥷 Vol réussi ! Vous repartez avec un beau pactole."
    )
  else:
    await update.message.reply_text(
        "🚨 Raté ! Vous vous êtes fait repérer par la police."
    )


async def police(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text(
      "👮 Plainte enregistrée auprès des forces de l'ordre."
  )


async def bail(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text("⚖️ Caution payée, vous êtes libéré(e).")


async def juge(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text(
      "⚖️ Le juge a rendu son verdict. Sentence appliquée."
  )


# ==========================================
# 🏷️ ENCHÈRES & OBJETS
# ==========================================


async def myitems(update: Update, context: ContextTypes.DEFAULT_TYPE):
  u = get_user(update.effective_user.id)
  items_str = ", ".join(u["items"]) if u["items"] else "Aucun objet"
  await update.message.reply_text(f"🎒 **Vos objets :** {items_str}")


async def shopitems(update: Update, context: ContextTypes.DEFAULT_TYPE):
  text = "🛍️ **Boutique de LifeCity :**\n"
  for id_item, info in items_shop.items():
    text += f"- [{id_item}] {info['name']} : {info['price']} €\n"
  await update.message.reply_text(text)


async def buyitem(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if not context.args:
    await update.message.reply_text("Utilisation : /buyitem id")
    return
  item_id = int(context.args[0])
  if item_id in items_shop:
    u = get_user(update.effective_user.id)
    u["items"].append(items_shop[item_id]["name"])
    await update.message.reply_text(
        f"✅ Achat réussi : {items_shop[item_id]['name']}"
    )
  else:
    await update.message.reply_text("❌ Objet introuvable.")


# ==========================================
# 🚀 LANCEMENT DU BOT
# ==========================================


def main():
  app = (
      ApplicationBuilder()
      .token("8027243153:AAGJleVVHIt5QYouPSUuOd025MKPzYjJHtM")
      .build()
  )

  # Profil & Économie
  app.add_handler(CommandHandler("start", start))
  app.add_handler(CommandHandler("me", me))
  app.add_handler(CommandHandler("acc", acc))
  app.add_handler(CommandHandler("daily", daily))
  app.add_handler(CommandHandler("work", work))
  app.add_handler(CommandHandler("pay", pay))
  app.add_handler(CommandHandler("richlist", richlist))
  app.add_handler(CommandHandler("leaderboard", leaderboard))
  app.add_handler(CommandHandler("topactif", topactif))

  # Banque
  app.add_handler(CommandHandler("bank", bank_list))
  app.add_handler(CommandHandler("openbank", openbank))
  app.add_handler(CommandHandler("depositbank", depositbank))
  app.add_handler(CommandHandler("withdrawbank", withdrawbank))
  app.add_handler(CommandHandler("balancebank", balancebank))
  app.add_handler(CommandHandler("loanbank", loanbank))
  app.add_handler(CommandHandler("repaybank", repaybank))
  app.add_handler(CommandHandler("loansbank", loansbank))

  # Famille & Social
  app.add_handler(CommandHandler("marry", marry))
  app.add_handler(CommandHandler("divorce", divorce))
  app.add_handler(CommandHandler("adopt", adopt))
  app.add_handler(CommandHandler("disown", disown))
  app.add_handler(CommandHandler("friend", friend))
  app.add_handler(CommandHandler("unfriend", unfriend))
  app.add_handler(CommandHandler("setfamilyname", setfamilyname))
  app.add_handler(CommandHandler("leave", leave_family))
  app.add_handler(CommandHandler("tree", tree))

  # Éducation
  app.add_handler(CommandHandler("diplome", diplome))

  # Entreprises & Finances
  app.add_handler(CommandHandler("creerboite", creerboite))
  app.add_handler(CommandHandler("listeboites", listeboites))
  app.add_handler(CommandHandler("infoboite", infoboite))
  app.add_handler(CommandHandler("monentreprise", monentreprise))
  app.add_handler(CommandHandler("postuler", postuler))
  app.add_handler(CommandHandler("demissionner", demissionner))
  app.add_handler(CommandHandler("parts", parts_cmd))
  app.add_handler(CommandHandler("versersalaires", versersalaires))

  # Casino & Jeux
  app.add_handler(CommandHandler("slots", slots))
  app.add_handler(CommandHandler("roulette", roulette_cmd))
  app.add_handler(CommandHandler("mines", mines))
  app.add_handler(CommandHandler("crash", crash))
  app.add_handler(CommandHandler("blackjack", blackjack))
  app.add_handler(CommandHandler("ppc", ppc))

  # Crime & Justice
  app.add_handler(CommandHandler("steal", steal))
  app.add_handler(CommandHandler("police", police))
  app.add_handler(CommandHandler("bail", bail))
  app.add_handler(CommandHandler("juge", juge))

  # Objets & Boutique
  app.add_handler(CommandHandler("myitems", myitems))
  app.add_handler(CommandHandler("shopitems", shopitems))
  app.add_handler(CommandHandler("buyitem", buyitem))

  print("🤖 Bot LifeCity en cours d'exécution...")
  app.run_polling()


if __name__ == "__main__":
  main()
