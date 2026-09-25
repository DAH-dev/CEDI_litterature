from .models import *


def panier_context(request):
    """Rend le nombre d'articles du panier disponible dans tous les templates."""
    panier = None
    nombre_articles = 0

    if request.user.is_authenticated:
        try:
            panier = Panier.objects.get(utilisateur=request.user)
        except Panier.DoesNotExist:
            panier = None
    else:
        session_key = request.session.session_key
        if session_key:
            try:
                panier = Panier.objects.get(session_id=session_key)
            except Panier.DoesNotExist:
                panier = None

    if panier:
        nombre_articles = sum(article.quantite for article in panier.articles.all())

    return {
        'nombre_articles_panier': nombre_articles,
        'categories_menu': Categorie.objects.all(),
    }