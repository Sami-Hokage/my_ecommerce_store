import os
import random
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.conf import settings
from faker import Faker
from store.models import Product, Variation, Category, Brand, ProductDescriptionSection

fake = Faker()


class Command(BaseCommand):
    help = "Seeds the database with real mobile names using existing Categories/Brands and static images"

    def handle(self, *args, **kwargs):
        # 1. Fetch real Categories and Brands from your database
        categories = list(Category.objects.all())
        brands = list(Brand.objects.all())

        if not categories or not brands:
            self.stdout.write(self.style.ERROR(
                "Missing Data: Please create at least one Category and Brand in the Admin panel first."
            ))
            return

        # 2. Define the path to your static images
        static_img_dir = os.path.join(settings.BASE_DIR, 'static', 'img')
        try:
            available_images = [f for f in os.listdir(static_img_dir)
                                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"Directory not found: {static_img_dir}"))
            return

        # 3. List of real-world mobile names for accuracy
        real_mobile_names = [
            "iPhone 15 Pro Max", "Samsung Galaxy S24 Ultra", "Google Pixel 8 Pro",
            "OnePlus 12", "Xiaomi 14 Ultra", "Nothing Phone (2)", "Sony Xperia 1 V",
            "Asus ROG Phone 8", "Motorola Edge 50 Pro", "Huawei P60 Pro"
        ]

        self.stdout.write(
            f"Found {len(categories)} categories, {len(brands)} brands, and {len(available_images)} images. Seeding...")

        for base_name in real_mobile_names:
            # Create a unique name to avoid slug conflicts
            full_name = f"{base_name} {random.randint(128, 512)}GB"
            price = random.randint(699, 1299)

            # Select a random image from your static/img folder
            selected_img = random.choice(available_images) if available_images else None

            # 4. Create the Product
            product = Product.objects.create(
                category=random.choice(categories),
                brand=random.choice(brands),
                product_name=full_name,
                slug=slugify(full_name),
                description=fake.paragraph(nb_sentences=5),
                specification=f"Latest flagship processor, OLED Display, {random.randint(8, 16)}GB RAM.",
                price=price,
                discount_price=price - 100 if random.choice([True, False]) else None,
                available=True,  # Matches your BooleanField
                image=f"products/{selected_img}" if selected_img else ""
            )

            # 5. Create Variations (Colors/Stock)
            # This ensures your 'total_stock' property works correctly
            colors = ['Titanium Black', 'Silver', 'Deep Purple', 'Midnight Blue']
            for color in random.sample(colors, k=2):
                Variation.objects.create(
                    product=product,
                    variation_category='color',
                    variation_value=color,
                    stock=random.randint(10, 50),
                    is_active=True
                )

            # 6. Add Description Sections
            ProductDescriptionSection.objects.create(
                product=product,
                title="Camera Performance",
                description="Capture stunning photos with the advanced triple-lens system and AI processing."
            )

        self.stdout.write(self.style.SUCCESS(f'Successfully seeded {len(real_mobile_names)} real mobile products!'))