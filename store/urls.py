from django.urls import path
from .views import HomeView, SignUpView, MyAccountView, CheckOutCartView, CheckOutInfoView, ProductView, ProfileUpdateView, ProductDetailView, SearchResultsView, AddToCartView,Cart,CartItem,Variation
from . import views

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('signup/', SignUpView.as_view(), name='signup'),
    path('account/', MyAccountView.as_view(), name='my_account'),
    path('profile/update/', ProfileUpdateView.as_view(), name='profile_update'),
    path('products/', ProductView.as_view(), name='products'),
    path('category/<slug:category_slug>/', views.ProductView.as_view(), name='category_products'),
    path('brand/<slug:brand_slug>/', views.ProductView.as_view(), name='brand_products'),
    path('product/<slug:category_slug>/<slug:product_slug>/', ProductDetailView.as_view(), name='product_detail'),
    path('submit_review/<int:product_id>/', views.submit_review, name='submit_review'),
    path('search/', views.SearchResultsView.as_view(), name='search_results'),
    path('new-arrivals/', views.NewArrivalView.as_view(), name='new_arrivals'),
    path('add_cart/<int:product_id>/', AddToCartView.as_view() , name='add_cart'),
    path('remove_cart/<int:product_id>/<int:cart_item_id>/', views.remove_cart, name='remove_cart'),
    path('checkout_cart/', CheckOutCartView.as_view(), name='checkout_cart'),
    path('checkout_info/', CheckOutInfoView.as_view(), name='checkout_info'),
    path('checkout_payment/', views.CheckOutPaymentView.as_view(), name='checkout_payment'),
    path('checkout_complete/', views.checkout_complete, name='checkout_complete'),
    path('manage_orders/', views.MyOrdersView.as_view(), name='manage_orders'),
    path('my_order_detail/<int:order_id>/', views.OrderDetailView.as_view(), name='my_order_detail'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('resend-otp/', views.resend_otp, name='resend_otp'),
    path('check-username/', views.check_username, name='check_username'),
    path('stripe-webhook/', views.stripe_webhook, name='stripe_webhook'),
]