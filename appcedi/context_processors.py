from .models import Panier, Categorie, ListeSouhaits

def panier_context(request):
    panier = None
    nombre_articles = 0
    souhaits_ids = []

    if request.user.is_authenticated:
        try:
            panier = Panier.objects.get(utilisateur=request.user)
        except Panier.DoesNotExist:
            pass
        
        # Récupérer tous les IDs des produits dans la wishlist
        souhaits_ids = list(ListeSouhaits.objects.filter(utilisateur=request.user).values_list('produit_id', flat=True))
    else:
        session_key = request.session.session_key
        if session_key:
            try:
                panier = Panier.objects.get(session_id=session_key)
            except Panier.DoesNotExist:
                pass

    if panier:
        nombre_articles = sum(article.quantite for article in panier.articles.all())

    return {
        'nombre_articles_panier': nombre_articles,
        'categories_menu': Categorie.objects.all(),
        'souhaits_ids': souhaits_ids, # 👈 Ajouté ici
    }