import base64, json
import importlib
from io import BytesIO
import tempfile

from django.contrib.auth.models import Group, User
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import clear_url_caches, resolve, reverse
from PIL import Image
from rest_framework.renderers import JSONRenderer
from rest_framework.test import APIClient
from .models import Author, Book, Review
from .serializers import AuthorSerializer, BookSerializer


class MediaServingTests(SimpleTestCase):
    def test_media_url_is_routed_in_debug_mode(self):
        urlconf = importlib.import_module(settings.ROOT_URLCONF)
        original_debug = settings.DEBUG
        try:
            with override_settings(DEBUG=True):
                importlib.reload(urlconf)
                clear_url_caches()
                resolved = resolve("/media/book_covers/cover.jpg")
                self.assertEqual(resolved.func.__module__, "django.views.static")
        finally:
            with override_settings(DEBUG=original_debug):
                importlib.reload(urlconf)
                clear_url_caches()


class HomePageTests(TestCase):
    def test_homepage_shows_login_without_exposing_api_or_admin_links(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bookshelf API")
        self.assertContains(response, "Books, authors, and stories.")
        self.assertContains(response, "ホームページの本")
        self.assertContains(response, "No books selected yet.")
        self.assertContains(response, 'href="/books/"')
        self.assertContains(response, 'href="/reviews/"')
        self.assertContains(response, 'href="/accounts/login/')
        self.assertContains(response, 'href="/accounts/signup/')
        self.assertNotContains(response, 'href="/api/books/"')
        self.assertNotContains(response, 'href="/api/reviews/"')
        self.assertNotContains(response, 'href="/api/authors/"')
        self.assertNotContains(response, 'href="/admin/"')

    def test_login_page_has_username_and_password_fields(self):
        response = self.client.get("/accounts/login/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="password"')
        self.assertContains(response, 'href="/accounts/signup/"')

    def test_signup_page_creates_regular_user_without_admin_fields(self):
        response = self.client.post(
            "/accounts/signup/",
            {
                "username": "new_reader",
                "password1": "StrongPassword!784",
                "password2": "StrongPassword!784",
                "is_staff": "on",
                "is_superuser": "on",
            },
        )

        self.assertRedirects(response, "/", fetch_redirect_response=False)
        user = User.objects.get(username="new_reader")
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(self.client.get("/api/books/").status_code, 403)
        admin_response = self.client.get("/admin/")
        self.assertEqual(admin_response.status_code, 302)
        self.assertIn("/admin/login/", admin_response["Location"])

    def test_signup_page_rejects_mismatched_passwords(self):
        response = self.client.post(
            "/accounts/signup/",
            {
                "username": "new_reader",
                "password1": "StrongPassword!784",
                "password2": "DifferentPassword!784",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("password2", response.context["form"].errors)
        self.assertFalse(User.objects.filter(username="new_reader").exists())

    def test_login_redirects_authenticated_user_to_next_page(self):
        user = User.objects.create_user(username="reader", password="password")

        response = self.client.post(
            "/accounts/login/",
            {"username": "reader", "password": "password", "next": "/api/books/"},
        )

        self.assertRedirects(response, "/api/books/", fetch_redirect_response=False)
        self.assertTrue(self.client.session.get("_auth_user_id"))
        self.assertEqual(self.client.get("/api/books/").status_code, 403)

    def test_staff_user_sees_read_only_api_links_but_not_admin_and_can_log_out(self):
        api_staff_group, _ = Group.objects.get_or_create(name="API Staff")
        user = User.objects.create_user(
            username="librarian",
            password="password",
        )
        user.groups.add(api_staff_group)
        self.client.force_login(user)

        response = self.client.get("/")

        self.assertContains(response, 'href="/api/books/"')
        self.assertContains(response, 'href="/api/authors/"')
        self.assertContains(response, 'href="/api/reviews/"')
        self.assertNotContains(response, 'href="/admin/"')
        self.assertContains(response, 'action="/accounts/logout/"')
        self.assertEqual(self.client.get("/api/books/").status_code, 200)
        self.assertEqual(self.client.post("/api/books/").status_code, 403)
        self.assertEqual(self.client.get("/admin/").status_code, 302)

        response = self.client.post("/accounts/logout/")

        self.assertRedirects(response, "/", fetch_redirect_response=False)
        self.assertNotIn("_auth_user_id", self.client.session)


class AuthorPageTests(TestCase):
    def test_homepage_displays_authors_and_links_to_author_pages(self):
        author = Author.objects.create(
            name="Jane Austen",
            country="England",
            birth_year=1775,
        )
        Book.objects.create(
            title="Pride and Prejudice",
            author=author,
            published_year=1813,
        )

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Authors")
        self.assertContains(response, "Jane Austen")
        self.assertContains(response, "England")
        self.assertContains(response, f"/authors/{author.id}/")
        self.assertNotContains(response, 'href="/api/authors/"')

    def test_authors_are_not_added_to_the_books_catalog(self):
        Author.objects.create(name="Jane Austen")

        response = self.client.get("/books/")

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "featured-authors")
        self.assertNotContains(response, "Jane Austen")

    def test_author_detail_displays_profile_books_and_api_link(self):
        author = Author.objects.create(
            name="Jane Austen",
            country="England",
            birth_year=1775,
        )
        book = Book.objects.create(
            title="Pride and Prejudice",
            author=author,
            published_year=1813,
        )

        response = self.client.get(f"/authors/{author.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Jane Austen")
        self.assertContains(response, "England")
        self.assertContains(response, "1775")
        self.assertContains(response, "Pride and Prejudice")
        self.assertContains(response, f"/books/{book.id}/")
        self.assertNotContains(response, f"/api/authors/{author.id}/")
        self.assertContains(response, 'href="/#featured-authors"')
        self.assertNotContains(response, 'href="/api/authors/"')

    def test_api_staff_can_open_author_api(self):
        author = Author.objects.create(name="Jane Austen")
        user = User.objects.create_user(username="reader", password="password")
        api_staff_group, _ = Group.objects.get_or_create(name="API Staff")
        user.groups.add(api_staff_group)
        self.client.force_login(user)

        response = self.client.get(f"/authors/{author.id}/")

        self.assertContains(response, f"/api/authors/{author.id}/")

    def test_author_detail_returns_404_for_unknown_author(self):
        response = self.client.get("/authors/9999/")

        self.assertEqual(response.status_code, 404)


class HomePageBookTests(TestCase):
    def test_homepage_only_displays_selected_books(self):
        author = Author.objects.create(name="Jane Austen", country="England")
        featured_book = Book.objects.create(
            title="Featured Book",
            author=author,
            published_year=1813,
            show_on_home=True,
        )
        Book.objects.create(
            title="Unlisted Book",
            author=author,
            published_year=1811,
        )

        response = self.client.get("/")

        self.assertContains(response, "Featured Book")
        self.assertNotContains(response, "Unlisted Book")
        self.assertContains(response, f"/books/{featured_book.id}/")

    def test_book_list_displays_books_instead_of_rest_api(self):
        author = Author.objects.create(name="Jane Austen", country="England")
        book = Book.objects.create(
            title="Catalog Book",
            author=author,
            published_year=1813,
        )

        response = self.client.get("/books/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "All books")
        self.assertContains(response, "Catalog Book")
        self.assertContains(response, f"/books/{book.id}/")
        self.assertNotContains(response, "/api/books/")

    def test_book_detail_shows_details_and_public_review_form(self):
        author = Author.objects.create(name="Jane Austen", country="England")
        book = Book.objects.create(
            title="Featured Book",
            author=author,
            published_year=1813,
            show_on_home=True,
        )
        Review.objects.create(
            book=book,
            reviewer_name="Reader",
            rating=5,
            comment="A lovely book.",
        )

        response = self.client.get(f"/books/{book.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bookshelf API")
        self.assertContains(response, "Featured Book")
        self.assertContains(response, "Jane Austen")
        self.assertContains(response, "A lovely book.")
        self.assertContains(response, "5.0 / 5")
        self.assertContains(response, "Write a review")
        self.assertContains(response, 'name="reviewer_name"')
        self.assertContains(response, 'name="comment"')
        self.assertNotContains(response, 'href="/api/books/')

    def test_anonymous_user_can_submit_review_from_book_page(self):
        book = Book.objects.create(
            title="Review Form Book",
            author=Author.objects.create(name="Review Form Author"),
            published_year=2020,
        )

        response = self.client.post(
            f"/books/{book.id}/",
            {
                "reviewer_name": "Reader",
                "rating": "5",
                "comment": "A wonderful story.",
            },
        )

        self.assertRedirects(
            response,
            f"/books/{book.id}/#reviews",
            fetch_redirect_response=False,
        )
        review = Review.objects.get(book=book)
        self.assertEqual(review.reviewer_name, "Reader")
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.comment, "A wonderful story.")

    def test_anonymous_invalid_review_submission_displays_form_errors(self):
        book = Book.objects.create(
            title="Review Form Book",
            author=Author.objects.create(name="Review Form Author"),
            published_year=2020,
        )

        response = self.client.post(
            f"/books/{book.id}/",
            {"reviewer_name": "", "rating": "6", "comment": ""},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This field is required.")
        self.assertContains(response, "Select a valid choice")
        self.assertFalse(Review.objects.filter(book=book).exists())

    def test_book_detail_returns_404_for_unknown_book(self):
        response = self.client.get("/books/9999/")

        self.assertEqual(response.status_code, 404)


class ReviewPageTests(TestCase):
    def setUp(self):
        author = Author.objects.create(name="Jane Austen", country="England")
        self.book = Book.objects.create(
            title="Pride and Prejudice",
            author=author,
            published_year=1813,
        )
        self.review = Review.objects.create(
            book=self.book,
            reviewer_name="Reader",
            rating=5,
            comment="A lovely book.",
        )

    def test_review_catalog_uses_site_design_and_links_to_review_detail(self):
        response = self.client.get("/reviews/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "All reviews")
        self.assertContains(response, "Reader")
        self.assertContains(response, "Pride and Prejudice")
        self.assertContains(response, "A lovely book.")
        self.assertContains(response, f"/reviews/{self.review.id}/")
        self.assertNotContains(response, f"/api/reviews/{self.review.id}/")

    def test_review_detail_hides_api_link_for_anonymous_users(self):
        response = self.client.get(f"/reviews/{self.review.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Reader")
        self.assertContains(response, "Pride and Prejudice")
        self.assertContains(response, "A lovely book.")
        self.assertNotContains(response, f"/api/reviews/{self.review.id}/")
        self.assertContains(response, 'href="/reviews/"')

    def test_api_staff_can_open_review_api(self):
        user = User.objects.create_user(username="reader", password="password")
        api_staff_group, _ = Group.objects.get_or_create(name="API Staff")
        user.groups.add(api_staff_group)
        self.client.force_login(user)

        response = self.client.get(f"/reviews/{self.review.id}/")

        self.assertContains(response, f"/api/reviews/{self.review.id}/")

    def test_review_detail_returns_404_for_unknown_review(self):
        response = self.client.get("/reviews/9999/")

        self.assertEqual(response.status_code, 404)

    def test_review_catalog_shows_empty_state(self):
        self.review.delete()

        response = self.client.get("/reviews/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No reviews have been added yet.")


class AuthenticationAccessTests(TestCase):
    def test_api_endpoints_require_authentication(self):
        for endpoint in ("/api/books/", "/api/authors/", "/api/reviews/"):
            with self.subTest(endpoint=endpoint):
                response = self.client.get(endpoint)
                self.assertEqual(response.status_code, 403)

    def test_regular_user_cannot_access_api_endpoints(self):
        user = User.objects.create_user(username="reader", password="password")
        self.client.force_login(user)

        for endpoint in ("/api/books/", "/api/authors/", "/api/reviews/"):
            with self.subTest(endpoint=endpoint):
                response = self.client.get(endpoint)
                self.assertEqual(response.status_code, 403)

    def test_api_staff_has_read_only_api_access(self):
        api_staff_group, _ = Group.objects.get_or_create(name="API Staff")
        user = User.objects.create_user(username="librarian", password="password")
        user.groups.add(api_staff_group)
        self.client.force_login(user)

        for endpoint in ("/api/books/", "/api/authors/", "/api/reviews/"):
            with self.subTest(endpoint=endpoint):
                self.assertEqual(self.client.get(endpoint).status_code, 200)
                self.assertEqual(self.client.post(endpoint).status_code, 403)

    def test_superuser_has_full_api_access(self):
        user = User.objects.create_superuser("fn0001", "admin@example.com", "password")
        self.client.force_login(user)

        for endpoint in ("/api/books/", "/api/authors/", "/api/reviews/"):
            with self.subTest(endpoint=endpoint):
                self.assertEqual(self.client.get(endpoint).status_code, 200)

    def test_django_admin_requires_staff_login(self):
        response = self.client.get("/admin/")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

    def test_fn0001_superuser_can_access_django_admin(self):
        User.objects.create_superuser("fn0001", "admin@example.com", "password")
        self.client.login(username="fn0001", password="password")

        response = self.client.get("/admin/")

        self.assertEqual(response.status_code, 200)

    def test_api_staff_cannot_access_django_admin(self):
        api_staff_group, _ = Group.objects.get_or_create(name="API Staff")
        user = User.objects.create_user(username="librarian", password="password")
        user.groups.add(api_staff_group)
        self.client.force_login(user)

        response = self.client.get("/admin/")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

    def test_regular_user_cannot_access_django_admin(self):
        user = User.objects.create_user(username="reader", password="password")
        self.client.force_login(user)

        response = self.client.get("/admin/")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])


class BookAdminCoverTests(TestCase):
    def setUp(self):
        self.media_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.media_dir.cleanup)
        media_settings = override_settings(MEDIA_ROOT=self.media_dir.name)
        media_settings.enable()
        self.addCleanup(media_settings.disable)

        self.author = Author.objects.create(name="Jane Austen", country="England")
        admin_user = User.objects.create_superuser("admin", "admin@example.com", "password")
        self.client.force_login(admin_user)

    def test_admin_can_upload_cover_and_select_book_for_home(self):
        image_data = BytesIO()
        Image.new("RGB", (2, 2), color="blue").save(image_data, format="JPEG")
        image = SimpleUploadedFile(
            "cover.jpg",
            image_data.getvalue(),
            content_type="image/jpeg",
        )

        response = self.client.post(
            reverse("admin:library_book_add"),
            {
                "title": "Featured Book",
                "author": self.author.pk,
                "published_year": 1813,
                "isbn": "",
                "in_stock": "on",
                "cover_image": image,
                "show_on_home": "on",
                "_save": "Save",
            },
        )

        self.assertEqual(response.status_code, 302)
        book = Book.objects.get(title="Featured Book")
        self.assertTrue(book.show_on_home)
        self.assertTrue(book.cover_image)

        homepage = self.client.get("/")
        self.assertContains(homepage, book.cover_image.url)
        self.assertContains(homepage, "Featured Book")

        changelist = self.client.get(reverse("admin:library_book_changelist"))
        self.assertContains(changelist, book.cover_image.url)
        self.assertContains(changelist, "Bookshelf Administration")
        self.assertContains(changelist, "library/css/admin.css")


class LessonFlow(TestCase):
    def setUp(self):
        m = Author.objects.create(name="Haruki Murakami", country="Japan", birth_year=1949)
        self.s = Author.objects.create(name="Natsume Soseki", country="Japan", birth_year=1867)
        r = Author.objects.create(name="Jose Rizal", country="Philippines", birth_year=1861)
        Book.objects.create(title="Kafka on the Shore", author=m, published_year=2002)
        Book.objects.create(title="Norwegian Wood", author=m, published_year=1987)
        Book.objects.create(title="Kokoro", author=self.s, published_year=1914)
        Book.objects.create(title="Noli Me Tangere", author=r, published_year=1887)
        Book.objects.create(title="El Filibusterismo", author=r, published_year=1891, in_stock=False)
        User.objects.create_superuser("admin", "a@a.com", "pw12345")
        tok = base64.b64encode(b"admin:pw12345").decode()
        self.auth = {"HTTP_AUTHORIZATION": f"Basic {tok}"}
        self.c = APIClient()

    def test_part2_shell(self):
        b = Book.objects.get(title="Kokoro")
        print(JSONRenderer().render(BookSerializer(b).data))
        print(json.dumps(AuthorSerializer(Author.objects.get(name="Jose Rizal")).data, default=str))
        bad = BookSerializer(data={"title": "Future Book", "author": self.s.id, "published_year": 2099})
        self.assertFalse(bad.is_valid()); print(bad.errors)
        good = BookSerializer(data={"title": "Botchan", "author": self.s.id, "published_year": 1906})
        self.assertTrue(good.is_valid()); good.save()
        isbn = BookSerializer(data={"title": "X", "author": self.s.id, "published_year": 1900, "isbn": "12AB"})
        self.assertFalse(isbn.is_valid()); print(isbn.errors)
        # two empty ISBNs should not clash
        for t in ("A", "B"):
            e = BookSerializer(data={"title": t, "author": self.s.id, "published_year": 1900, "isbn": ""})
            self.assertTrue(e.is_valid(), e.errors); e.save()

    def test_part3_4_crud_filters_perms(self):
        c = self.c
        r = c.get("/api/books/"); self.assertEqual(r.status_code, 403)
        r = c.get("/api/books/", **self.auth); self.assertEqual(r.status_code, 200); print(r.json()["count"], r.json()["next"])
        body = {"title": "Sanshiro", "author": self.s.id, "published_year": 1908}
        r = c.post("/api/books/", body, format="json"); print("anon POST", r.status_code, r.json())
        self.assertEqual(r.status_code, 403)
        r = c.post("/api/books/", body, format="json", **self.auth); self.assertEqual(r.status_code, 201); print(r.json())
        bid = r.json()["id"]
        r = c.patch(f"/api/books/{bid}/", {"in_stock": False}, format="json", **self.auth); self.assertEqual(r.status_code, 200)
        r = c.put(f"/api/books/{bid}/", {"title": "Only"}, format="json", **self.auth); print("PUT partial", r.status_code, r.json())
        self.assertEqual(r.status_code, 400)
        r = c.post("/api/books/", {"title": ""}, format="json", **self.auth); print(r.status_code, r.json())
        r = c.post("/api/books/", {"title": "X", "author": "Natsume Soseki", "published_year": 1900}, format="json", **self.auth); print(r.json())
        r = c.post("/api/books/1/", body, format="json", **self.auth); print("POST detail", r.status_code)
        self.assertEqual(c.get("/api/books/9999/", **self.auth).status_code, 404)
        r = c.delete(f"/api/books/{bid}/", **self.auth); self.assertEqual(r.status_code, 204)
        def titles(q): return [b["title"] for b in c.get("/api/books/" + q, **self.auth).json()["results"]]
        print("search", titles("?search=murakami"))
        print("in_stock", titles("?in_stock=false"))
        print("gte", c.get("/api/books/?published_year__gte=1900", **self.auth).json()["count"])
        print("order", titles("?ordering=title"))
        a = Author.objects.get(name="Jose Rizal").id
        print("author", titles(f"?author={a}&ordering=published_year"))
        print("page2", titles("?page=2"))
        r = c.get("/api/authors/?country=Japan", **self.auth); print(r.json()["results"][0])
        # browsable API with filters renders
        r = c.get("/api/books/", HTTP_ACCEPT="text/html", **self.auth); self.assertEqual(r.status_code, 200)

    def test_part5_reviews(self):
        c = self.c
        k = c.get("/api/books/?search=kokoro", **self.auth).json()["results"][0]
        for n, rt in (("Aiko", 5), ("Ben", 4)):
            r = c.post("/api/reviews/", {"book": k["id"], "reviewer_name": n, "rating": rt}, format="json", **self.auth)
            self.assertEqual(r.status_code, 201, r.json())
        print(c.get(f"/api/reviews/?book={k['id']}", **self.auth).json()["count"])
        avg = c.get(f"/api/books/{k['id']}/", **self.auth).json()["average_rating"]; print("avg", avg); self.assertEqual(avg, 4.5)
        r = c.post("/api/reviews/", {"book": k["id"], "reviewer_name": "C", "rating": 6}, format="json", **self.auth)
        print(r.status_code, r.json())
        top = c.get("/api/books/?ordering=-avg_rating", **self.auth).json()["results"][0]["title"]; print("top", top); self.assertEqual(top, "Kokoro")
