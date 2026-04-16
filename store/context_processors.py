from .models import Category, Brand, Product, Cart, CartItem
from .views import _cart_id

def category_list(request):
    # This fetches all categories from PostgreSQL and makes them
    # available in every template as the variable 'categories'
    return {
        'categories': Category.objects.all().order_by('category_name')
    }
def store_context(request):
    return {
        'categories': Category.objects.all().order_by('category_name'),
        'brands': Brand.objects.all().order_by('brand_name')
    }
def menu_list(request):
    return {'categories': Category.objects.all().order_by('category_name')}

def menu_links(request):
    links_brand = Brand.objects.all()

    popular_phones = Product.objects.filter(
        category__category_name__icontains='Mobile',
        available=True
    ).order_by('-id')[:12]


    return {
        'links_brand': links_brand,
        'popular_phones': popular_phones
    }


def cart_details(request):
    cart_items = []
    cart_count = 0
    cart_total = 0

    try:
        # Get the single cart object directly
        cart = Cart.objects.get(cart_id=_cart_id(request))
        cart_items = CartItem.objects.filter(cart=cart, is_active=True)

        for item in cart_items:
            cart_total += (item.product.price * item.quantity)
            cart_count += item.quantity
    except (Cart.DoesNotExist, Exception):
        # Fallback if cart doesn't exist yet
        pass

    return {
        'cart_items_header': cart_items,  # This is the variable name for your loop
        'cart_count': cart_count,
        'cart_total': cart_total,
    }
