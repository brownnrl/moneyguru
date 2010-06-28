<%!
	title = 'Gestion de liquidités'
	selected_menu_item = 'liquide'
%>
<%inherit file="/fr/base_mg.mako"/>

La gestion de liquidités est difficile dans toutes les applications. L'argent que vous avez en poche est techniquement un actif, mais un actif pour lequel vous ne voulez pas nécessairement enregistrer toutes les transactions. En effet, il peut devenir très lourd (et peu pertinent) d'enregistrer chaque petite dépense que vous faites. Par contre, on veut quand même enregistrer les transaction liquide pertinentes. Comment faire pour enregistrer ces transactions tout en ayant un compte de liquidités qui aie du sens?

**Le compte de dépense "Liquidités"**. La solution proposée dans moneyGuru est de créer un compte de dépense "Liquidités". Quand vous retirez de l'argent à la banque, vous envoyez cette argent à ce compte de dépense. Puis, quand vous achetez quelque chose avec cette argent, vous prenez votre compte "Liquidité" comme source. Ainsi, vous aurez une dépense "Liquidités" qui correspond, en fin de compte, à toutes les dépenses en liquide que vous n'aurez pas pris la peine d'enregistrer (ou bien les sous que vous avez perdus dans le divan).