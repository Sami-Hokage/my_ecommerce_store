from itertools import product as iter_product
import stripe

import random

from datetime import timedelta
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.conf import settings

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, CreateView, TemplateView, DetailView
from django.views.generic.edit import UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from .forms import CustomUserCreationForm, UserUpdateForm, OrderForm
from .models import Product, User, Category, Brand, Review, Variation, Cart, CartItem, Order, OrderProduct
from django.db.models import Q, F
from django.core.exceptions import ObjectDoesNotExist
from django.views import View
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.contrib.sites.shortcuts import get_current_site
from .tokens import generate_token
from django.contrib.auth.decorators import login_required


# Create your views here.

def _cart_id(request):
    cart = request.session.session_key
    if not cart:

        request.session.create()
        cart = request.session.session_key
    return cart

class HomeView(TemplateView):
    template_name = 'index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        main_item = Product.objects.filter(product_name__icontains='iphone 6S', available=True).first()
        context['main_promo'] = main_item
        other_promos = Product.objects.filter(is_promoted=True, available=True).exclude(id=main_item.id).order_by('-created')[:5]


        if other_promos.count() >= 4:
            context['blue_promo'] = other_promos[0]
            context['silver_promo_1'] = other_promos[1]
            context['silver_promo_2'] = other_promos[2]
            context['black_promo'] = other_promos[3]



        context['trending_items'] = Product.objects.filter(available=True, is_promoted=True).order_by('-views')[:12]

        context['tablet'] = Product.objects.filter(
            category__category_name__iexact='tablet',
            available=True
        ).order_by('-views')[:8]

        context['mobile_phones'] = Product.objects.filter(
            category__category_name__iexact='Mobile Phones',
            available=True
        ).order_by('-views')[:8]

        context['brands'] = Brand.objects.all()

        return context


class ProductDetailView(DetailView):
    model = Product
    template_name = 'product_detail.html'
    context_object_name = 'product'

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)

        self.object.views = F('views') + 1
        self.object.save(update_fields=['views'])

        return response

    def get_object(self, queryset=None):


        category_slug = self.kwargs.get('category_slug')
        product_slug = self.kwargs.get('product_slug')


        return get_object_or_404(
            Product,
            category__slug=category_slug,
            slug=product_slug
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_product = self.object
        context['colors'] = Variation.objects.filter(product=self.get_object(), variation_category='color', is_active=True)
        context['similar_products'] = Product.objects.filter(
            category=current_product.category,
            available=True
        ).exclude(id=current_product.id)[:6]

        return context

class NewArrivalView(ListView):
    model = Product
    template_name = 'product.html'
    context_object_name = 'products'
    paginate_by = 6

    def get_queryset(self):

        return Product.objects.filter(available=True).order_by('-created')[:10]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['products_count'] = self.get_queryset().count()
        context['title'] = "New Arrivals" # Dynamic title for the header
        return context


class ProductView(TemplateView):
    template_name = 'product.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        query = self.request.GET.get('q')
        category_slug = self.kwargs.get('category_slug')
        brand_slug = self.kwargs.get('brand_slug')  # New: Get brand from URL

        products = Product.objects.filter(available=True)


        if query:

            keywords = query.split()


            search_filter = Q()

            for word in keywords:

                singular_word = word[:-1] if word.lower().endswith('s') else word

                search_filter &= (
                        Q(product_name__icontains=word) |
                        Q(product_name__icontains=singular_word) |
                        Q(description__icontains=word) |
                        Q(category__category_name__icontains=word) |
                        Q(category__category_name__icontains=singular_word) |
                        Q(brand__brand_name__icontains=word)
                )

            products = products.filter(search_filter).distinct()
            context['filter_title'] = f"Search: {query}"


        elif category_slug:
            category = get_object_or_404(Category, slug=category_slug)
            products = products.filter(category=category)
            context['filter_title'] = category.category_name


        elif brand_slug:
            brand = get_object_or_404(Brand, slug=brand_slug)
            products = products.filter(brand=brand)
            context['filter_title'] = brand.brand_name

        else:
            context['filter_title'] = "Our Store"

        context['products'] = products
        context['categories'] = Category.objects.all()
        context['links_brand'] = Brand.objects.all()  # Good for the sidebar
        return context


def send_otp_handler(request, user):
    """Helper function to manage OTP generation and timing logic"""
    now = timezone.now()
    last_sent = request.session.get('otp_last_sent')

    # Enforce 120 second gap server-side
    if last_sent:
        elapsed = (now - timezone.datetime.fromisoformat(last_sent)).total_seconds()
        if elapsed < 120:
            return False, int(120 - elapsed)

    otp = str(random.randint(100000, 999999))

    # Store OTP and Expiry (10 mins) and Last Sent (for 120s gap)
    request.session['registration_otp'] = otp
    request.session['otp_expiry'] = (now + timedelta(minutes=10)).isoformat()
    request.session['otp_last_sent'] = now.isoformat()
    request.session['temp_user_id'] = user.id

    subject = 'Verify your my_ecommerce Account'
    # Use render_to_string for the styled email if preferred, or plain text here
    message = f'Hi {user.username}, your verification code is {otp}. It expires in 10 minutes.'
    send_mail(subject, message, settings.EMAIL_HOST_USER, [user.email])

    return True, 0

class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    template_name = 'registration/signup.html'

    def form_valid(self, form):
        # 1. Save the user (is_active is already False by default in models.py)
        user = form.save()

        # 2. Prepare the verification email
        current_site = get_current_site(self.request)
        mail_subject = 'Activate your account'
        message = render_to_string('registration/activation_email.html', {
            'user': user,
            'domain': current_site.domain,
            'uid': urlsafe_base64_encode(force_bytes(user.pk)),
            'token': generate_token.make_token(user),
        })

        # 3. Send the email using your Gmail App Password credentials
        to_email = form.cleaned_data.get('email')
        email = EmailMessage(mail_subject, message, to=[to_email])
        email.send()

        # 4. Show a success page telling them to check their inbox
        return render(self.request, 'registration/check_email.html')

def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and generate_token.check_token(user, token):
        user.is_active = True # Now they can finally log in!
        user.save()
        return redirect('login')
    else:
        return render(request, 'registration/activation_invalid.html')


def resend_otp(request):
    user_id = request.session.get('temp_user_id')
    if not user_id:
        return redirect('signup')

    user = get_object_or_404(User, id=user_id)
    success, wait_time = send_otp_handler(request, user)
    if success:
        messages.success(request, 'New code sent!')
    else:
        messages.error(request, f'Please wait {wait_time}s before resending.')

    return redirect('verify_otp')  # Always redirect back to the verification page

def check_username(request):
    username = request.GET.get('username', None)
    data = {
        'is_taken': User.objects.filter(username__iexact=username).exists()
    }
    return JsonResponse(data)

class MyAccountView(TemplateView):
    template_name = 'my_account.html'
    def get_context_data(self, **kwargs):
        context = super(MyAccountView, self).get_context_data(**kwargs)
        return context


class CheckOutInfoView(LoginRequiredMixin, TemplateView):
    login_url = 'login'
    template_name = 'outflow_cart/checkout_info.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        total = 0
        quantity = 0

        try:

            cart = Cart.objects.get(cart_id=_cart_id(self.request))
            cart_items = CartItem.objects.filter(cart=cart, is_active=True)

            for cart_item in cart_items:
                total += cart_item.sub_total()
                quantity += cart_item.quantity

            context['cart_items'] = cart_items
        except ObjectDoesNotExist:
            context['cart_items'] = []

        context['total'] = total
        context['quantity'] = quantity


        order_id = self.request.session.get('order_id')
        if order_id:
            try:

                order = Order.objects.get(id=order_id, user=self.request.user)

                context['form'] = OrderForm(instance=order)
            except Order.DoesNotExist:
                context['form'] = OrderForm()
        else:
            context['form'] = OrderForm()

        return context

    def post(self, request):
        total = 0
        tax = 0
        try:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_items = CartItem.objects.filter(cart=cart, is_active=True)
            for item in cart_items:
                total += (item.product.price * item.quantity)

            tax = (5 * total) / 100
            grand_total = total + tax
        except ObjectDoesNotExist:
            return redirect('checkout_cart')
        order_id = request.session.get('order_id')


        order_data = {
            'user': request.user,
            'first_name': request.POST.get('first_name'),
            'last_name': request.POST.get('last_name'),
            'company_name': request.POST.get('company_name'),  # Added
            'area_code': request.POST.get('area_code'),  # Added
            'phone': request.POST.get('phone'),
            'email': request.user.email,
            'address_line_1': request.POST.get('address_line_1'),
            'address_line_2': request.POST.get('address_line_2'),
            'city': request.POST.get('city'),
            'country': request.POST.get('country'),
            'zip_code': request.POST.get('zip_code'),
            'order_total': grand_total,
            'tax': tax,
            'ip': request.META.get('REMOTE_ADDR')
        }

        if order_id:

            Order.objects.filter(id=order_id).update(**order_data)
            order = Order.objects.get(id=order_id)
        else:

            order = Order.objects.create(**order_data)
            request.session['order_id'] = order.id

        return redirect('checkout_payment')



class SearchResultsView(ListView):
    model = Product
    template_name = 'search_results.html'
    context_object_name = 'products'

    def get_queryset(self):
        query = self.request.GET.get('q')
        sort = self.request.GET.get('sort', '-created')

        products = Product.objects.filter(available=True)

        if query:
            search_terms = {query, query.rstrip('s'), query.rstrip('es')}


            q_objects = Q()
            for term in search_terms:
                if len(term) > 2:
                    q_objects |= Q(product_name__icontains=term)
                    q_objects |= Q(description__icontains=term)
                    q_objects |= Q(category__category_name__icontains=term)
                    q_objects |= Q(brand__brand_name__icontains=term)
            products = products.filter(q_objects)

        if sort =='popular':

            products = products.order_by('-is_promoted', '-created')
        else:
            products = products.order_by(sort)


        return products.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['categories'] = Category.objects.all()
        context['brand'] = Brand.objects.all()


        context['query'] = self.request.GET.get('q')
        context['products_count'] = context['products'].count() if context['products'] else 0

        return context

class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserUpdateForm
    template_name = 'profile_update.html'
    success_url = reverse_lazy('my_account')

    def get_object(self):

        return self.request.user


def submit_review(request, product_id):
    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id)


        name = request.POST.get('name')
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        rating = request.POST.get('rating')


        Review.objects.create(
            product=product,
            name=name,
            subject=subject,
            message=message,
            rating=rating
        )

        return redirect('product_detail', slug=product.slug)


class AddToCartView(View):

    def get(self, request, product_id):
        return self.post(request, product_id)

    def post(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        product_variation = []

        data = request.POST if request.method == 'POST' else request.GET

        for key, value in data.items():
            try:
                variation = Variation.objects.get(
                    product=product,
                    variation_category__iexact=key,
                    variation_value__iexact=value
                )
                product_variation.append(variation)
            except Variation.DoesNotExist:
                pass


        cart, _ = Cart.objects.get_or_create(cart_id=_cart_id(request))


        cart_items = CartItem.objects.filter(product=product, cart=cart)
        if cart_items.exists():
            ex_var_list = [list(item.variations.all()) for item in cart_items]
            if product_variation in ex_var_list:

                item = cart_items[ex_var_list.index(product_variation)]
                item.quantity += 1
                item.save()
            else:

                item = CartItem.objects.create(product=product, quantity=1, cart=cart)
                if product_variation:
                    item.variations.add(*product_variation)
                item.save()
        else:

            item = CartItem.objects.create(product=product, quantity=1, cart=cart, is_active=True)
            if product_variation:
                item.variations.add(*product_variation)
            item.save()

        return redirect('checkout_cart')

def remove_cart(request, product_id, cart_item_id):
    cart = Cart.objects.get(cart_id=_cart_id(request))
    product = get_object_or_404(Product, id=product_id)
    try:

        cart_item = CartItem.objects.get(product=product, cart=cart, id=cart_item_id)
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
        else:
            cart_item.delete()
    except ObjectDoesNotExist:
        pass
    return redirect('checkout_cart')


class CheckOutCartView(TemplateView):
    template_name = 'outflow_cart/checkout_cart.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        total = 0

        quantity = 0
        try:
            cart = Cart.objects.get(cart_id=_cart_id(self.request))
            cart_items = CartItem.objects.filter(cart=cart, is_active=True)
            for cart_item in cart_items:
                total += cart_item.sub_total()
                quantity += cart_item.quantity
            context['cart_items'] = cart_items
        except ObjectDoesNotExist:
            context['cart_items'] = []

        tax = (5* total) / 100
        grand_total = total + tax

        context['grand_total'] = grand_total
        context['tax'] = tax
        context['total'] = total
        context['quantity'] = quantity
        return context

stripe.api_key = settings.STRIPE_SECRET_KEY
class CheckOutPaymentView(LoginRequiredMixin, TemplateView):
    login_url = 'login'
    template_name = 'outflow_cart/checkout_payment.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)


        order_id = self.request.session.get('order_id')
        try:
            order = Order.objects.get(id=order_id, user=self.request.user)
            context['order'] = order


            cart = Cart.objects.get(cart_id=_cart_id(self.request))
            cart_items = CartItem.objects.filter(cart=cart, is_active=True)
            context['cart_items'] = cart_items


            total = 0
            for item in cart_items:
                total += item.sub_total()

            tax = (5 * total) / 100
            grand_total = total + tax

            context.update({
                'total': total,
                'tax': tax,
                'grand_total': grand_total,
            })

        except (ObjectDoesNotExist, Order.DoesNotExist):

            pass

        return context

    def post(self, request, *args, **kwargs):
        order_id = request.session.get('order_id')
        order = get_object_or_404(Order, id=order_id, user=request.user)
        token = request.POST.get('stripeToken')

        if not token:
            from django.contrib import messages
            messages.error(request, "Payment token missing. Please ensure JavaScript is enabled.")
            return redirect('checkout_payment')



        cart_items = CartItem.objects.filter(cart__cart_id=_cart_id(request))
        total = 0
        for item in cart_items:
            total += item.sub_total()

        tax = (5 * total) / 100
        grand_total = total + tax

        try:
            charge = stripe.Charge.create(
                amount=int(grand_total * 100),
                currency='usd',
                description=f'Order #{order.id}',
                source=token,
            )

            order.payment_id = charge.id
            order.order_total = grand_total
            order.tax = tax
            order.is_ordered = True
            order.status = 'Accepted'
            order.save()


            cart_items = CartItem.objects.filter(cart__cart_id=_cart_id(request))

            for item in cart_items:
                order_product = OrderProduct()
                order_product.order_id = order.id
                order_product.user = request.user
                order_product.product_id = item.product_id
                order_product.quantity = item.quantity
                order_product.product_price = item.product.discount_price if (item.product.discount_price and item.product.discount_price > 0) else item.product.price
                order_product.ordered = True
                order_product.save()


                item_variations = item.variations.all()
                order_product.variations.set(item_variations.all())
                order_product.save()


            current_cart_id = _cart_id(request)
            CartItem.objects.filter(cart__cart_id=current_cart_id).delete()


            if 'order_id' in request.session:
                del request.session['order_id']

            return redirect(f"{reverse('checkout_complete')}?order_number={order.id}")

        except stripe.error.CardError as e:
            return render(request, self.template_name, {'error': e.user_message})


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    # Handle the successful charge event
    if event['type'] == 'charge.succeeded':
        charge = event['data']['object']
        payment_id = charge['id']

        try:
            order = Order.objects.get(payment_id=payment_id)
            if not order.is_ordered:
                order.is_ordered = True
                order.status = 'Accepted'
                order.save()
                # You could also trigger an email to the customer here
        except Order.DoesNotExist:
            pass

    return HttpResponse(status=200)

stripe.api_key = settings.STRIPE_SECRET_KEY



def checkout_complete(request):
    order_number = request.GET.get('order_number')
    try:
        order = Order.objects.get(id=order_number, user=request.user)
        return render(request, 'outflow_cart/checkout_complete.html', {'order': order})
    except Order.DoesNotExist:
        return redirect('home')

class MyOrdersView(LoginRequiredMixin, ListView):
    model = Order
    template_name = 'outflow_cart/manage_orders.html'
    context_object_name = 'orders'

    def get_queryset(self):

        return Order.objects.filter(user=self.request.user, is_ordered=True).order_by('-created_at')

class OrderDetailView(LoginRequiredMixin, DetailView):
    model = Order
    template_name = 'outflow_cart/my_order_details.html'
    context_object_name = 'order'

    def get_object(self, queryset=None):

        return get_object_or_404(Order, id=self.kwargs.get('order_id'), user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['order_items'] = OrderProduct.objects.filter(order=self.object)
        return context