from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Category, Product, Brand, Review, Variation, ProductImage, ProductDescriptionSection, ProductAdditionalInfo, Cart, CartItem, Order, OrderProduct, OTPVerification
# Import your custom User model


class AccountAdmin(UserAdmin):
    # Columns shown in the admin list view
    list_display = ('email', 'first_name', 'last_name', 'username', 'last_login', 'date_joined', 'is_active')

    # Make these fields clickable to enter the user's profile
    list_display_links = ('email', 'first_name', 'last_name')

    # Fields that you don't want the admin to edit manually
    readonly_fields = ('last_login', 'date_joined')

    # Sort by newest members first
    ordering = ('-date_joined',)

    # These four are required when overriding the default UserAdmin
    filter_horizontal = ()
    list_filter = ()
    fieldsets = ()


# Register your custom User model with the custom Admin class
admin.site.register(User, AccountAdmin)


# New models Category and Product
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['category_name', 'slug']
    prepopulated_fields = {'slug': ('category_name',)}

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['brand_name', 'slug', 'brand_image']
    prepopulated_fields = {'slug': ('brand_name',)}

class ReviewInline(admin.TabularInline):
    model = Review
    extra = 0
    readonly_fields = ('name', 'rating', 'subject', 'message', 'created_at')

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3

class DescriptionSectionInline(admin.TabularInline):
    model = ProductDescriptionSection
    extra = 3

class AdditionalInfoInline(admin.TabularInline):
    model = ProductAdditionalInfo
    extra = 1

class VariationInline(admin.TabularInline):
    model = Variation
    extra = 1

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'name', 'rating', 'subject', 'created_at')
    list_filter = ('rating', 'created_at', 'product')
    search_fields = ('name', 'email', 'subject', 'message')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['product_name', 'slug', 'price', 'discount_price', 'total_stock', 'available', 'created', 'updated']
    list_filter = ['available', 'created', 'updated']
    list_editable = ['price', 'discount_price', 'available']
    prepopulated_fields = {'slug': ('product_name',)}
    inlines = [VariationInline, ReviewInline, ProductImageInline, DescriptionSectionInline, AdditionalInfoInline]

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('cart_id', 'date_added')

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('product', 'cart', 'quantity', 'is_active')

class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'first_name', 'last_name', 'email', 'city', 'country', 'order_total', 'status', 'is_ordered', 'created_at']
    list_filter = ['status', 'is_ordered']
    search_fields = ['first_name', 'last_name', 'phone', 'email']
    list_per_page = 20

admin.site.register(Order, OrderAdmin)


@admin.register(OrderProduct)
class OrderProductAdmin(admin.ModelAdmin):
    list_display = ['order_id', 'order', 'user', 'product', 'product_price', 'ordered','created_at', 'updated_at']


@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):

    list_display = ('user', 'otp_code', 'created_at', 'is_expired_status')


    search_fields = ('user__email', 'user__username', 'otp_code')


    def is_expired_status(self, obj):
        return obj.is_expired()

    is_expired_status.boolean = True
    is_expired_status.short_description = 'Has Expired?'