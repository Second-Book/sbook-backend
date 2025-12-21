---
name: SecondBook Improvement Plan
overview: Create a detailed development roadmap document (improvement-plan.md) for SecondBook platform based on code review findings. This task produces documentation, NOT implementation.
todos:
  - id: security-config
    content: Fix CORS, DEBUG, password validators in backend settings
    status: pending
  - id: rate-limiting
    content: Add django-ratelimit to auth endpoints
    status: pending
  - id: input-validation
    content: Add price/email validation and XSS sanitization
    status: pending
  - id: user-serializer
    content: Fix UserSerializer to expose only safe fields
    status: pending
  - id: token-storage
    content: Make frontend token handling SSR-safe
    status: pending
  - id: websocket-block
    content: Fix is_blocked() to check specific recipient
    status: pending
  - id: remove-duplicates
    content: Remove duplicate ViewSets and custom permission
    status: pending
  - id: db-indexes
    content: Add database indexes on frequently queried fields
    status: pending
  - id: homepage
    content: Implement homepage with search bar and latest textbooks
    status: pending
  - id: textbook-detail
    content: Complete textbook detail page with contacts
    status: pending
  - id: chat-ui
    content: Implement WebSocket client and chat UI
    status: pending
  - id: edit-delete-listings
    content: Add edit/delete functionality for user listings
    status: pending
  - id: about-faq
    content: Create About/FAQ page
    status: pending
  - id: 404-page
    content: Create custom 404 error page
    status: pending
  - id: loading-states
    content: Add skeleton loaders and loading indicators
    status: pending
  - id: toast-notifications
    content: Add react-hot-toast for user feedback
    status: pending
  - id: pagination-ui
    content: Implement pagination component
    status: pending
  - id: image-upload
    content: Add image upload with preview
    status: pending
  - id: frontend-tests
    content: Setup Jest and write component tests
    status: pending
  - id: e2e-tests
    content: Setup Playwright and write E2E tests
    status: pending
  - id: api-docs
    content: Add drf-spectacular for Swagger docs
    status: pending
  - id: structured-logging
    content: Add structlog for JSON logging
    status: pending
---

# Plan: SecondBook Platform Improvement

## Цель работы

**Цель данной задачи:** Создание детального документа с планом разработки (development roadmap) для платформы SecondBook.**Результат:** Документ `improvement-plan.md`, который будет размещён в `/home/arezvov/projects/sbook/textbook-marketplace-frontend/docs/`.**Важно:** Данная задача НЕ включает непосредственную реализацию описанных улучшений. Документ служит техническим руководством для последующей разработки.---

## Обзор

Этот план адресует выводы из [code review](docs/code-review.md) в соответствии с [product vision](docs/product-vision.md). План разделён на фазы по приоритету.

## Phase 1: Critical Security Fixes (Week 1)

### 1.1 Backend Security Configuration

**Problem:** CORS misconfiguration, DEBUG mode enabled, password validators disabled.**Backend Changes:**File: `textbook_marketplace/textbook_marketplace/settings.py`

```python
# Production settings
DEBUG = config('DEBUG', default=False, cast=bool)

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    config('FRONTEND_URL', default='http://localhost:3000'),
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
```

**Checklist:**

- [ ] DEBUG=False in production .env
- [ ] CORS_ALLOW_ALL_ORIGINS=False
- [ ] CORS_ALLOWED_ORIGINS contains only trusted domains
- [ ] Password validators enabled
- [ ] Separate settings_prod.py file created

**Verification:** Run Django check: `python manage.py check --deploy`---

### 1.2 Rate Limiting

**Library:** `django-ratelimit`**Backend Changes:**File: `pyproject.toml` - add dependency:

```toml
"django-ratelimit==4.1.0",
```

File: `textbook_marketplace/marketplace/views.py`:

```python
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator

class SignupView(APIView):
    @method_decorator(ratelimit(key='ip', rate='5/m', method='POST', block=True))
    def post(self, request):
        # existing code
```

**Apply rate limiting to:**

- `/signup/` - 5 requests/minute
- `/token/` - 10 requests/minute  
- `/token/refresh/` - 20 requests/minute
- `/report/` - 3 requests/minute

**Checklist:**

- [ ] django-ratelimit installed
- [ ] Rate limiting on auth endpoints
- [ ] Rate limiting on report endpoint
- [ ] Tests for rate limiting

**Verification:** Test with curl: `for i in {1..10}; do curl -X POST localhost:8000/api/signup/; done`---

### 1.3 Input Validation

**Backend Changes:**File: `textbook_marketplace/marketplace/serializers.py`:

```python
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator

class TextbookSerializer(serializers.ModelSerializer):
    price = serializers.DecimalField(
        max_digits=6, 
        decimal_places=2,
        validators=[MinValueValidator(0.01), MaxValueValidator(99999.99)]
    )
    
    def validate_description(self, value):
        # Sanitize HTML/XSS
        import bleach
        return bleach.clean(value, tags=[], strip=True)

class SignupSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered")
        return value
```

**Add dependency:** `bleach==6.1.0`**Checklist:**

- [ ] Price validation (positive, max value)
- [ ] Email validation in signup
- [ ] XSS sanitization with bleach
- [ ] Phone number format validation (optional)

**Verification:** Test with invalid data: negative prices, XSS payloads in description---

### 1.4 Fix UserSerializer Data Exposure

**Problem:** `fields = '__all__'` exposes password hash.File: `textbook_marketplace/marketplace/serializers.py`:

```python
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 
                  'telegram_id', 'telephone', 'is_seller', 'date_joined']
        read_only_fields = ['id', 'date_joined']
```

**Checklist:**

- [ ] UserSerializer uses explicit safe fields
- [ ] No password or is_superuser exposed
- [ ] Tests verify no sensitive data in response

---

### 1.5 Frontend Token Storage Improvement

**Problem:** Tokens in localStorage vulnerable to XSS.**Option A (Recommended):** HttpOnly cookiesFile: `textbook_marketplace/textbook_marketplace/settings.py`:

```python
SIMPLE_JWT = {
    'AUTH_COOKIE': 'access_token',
    'AUTH_COOKIE_HTTP_ONLY': True,
    'AUTH_COOKIE_SECURE': True,  # HTTPS only
    'AUTH_COOKIE_SAMESITE': 'Lax',
}
```

**Option B (Minimal change):** Keep localStorage but add SSR checkFile: `src/services/api.ts`:

```typescript
const getAccessToken = (): string | null => {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('access_token');
};

apiClient.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
```

**Checklist:**

- [ ] SSR-safe localStorage access
- [ ] Token refresh logic handles SSR
- [ ] Consider httpOnly cookies for production

---

## Phase 2: Critical Bug Fixes (Week 1-2)

### 2.1 Fix WebSocket Block Logic

**Problem:** `is_blocked()` checks if user is in ANY block, not specific recipient.File: `textbook_marketplace/chat/consumers.py`:

```python
@database_sync_to_async
def is_blocked(self, recipient: User) -> bool:
    """Check if sender blocked recipient OR recipient blocked sender."""
    return Block.objects.filter(
        Q(initiator_user=recipient, blocked_user=self.user) |
        Q(initiator_user=self.user, blocked_user=recipient)
    ).exists()

async def receive(self, text_data: str):
    text_data_json = json.loads(text_data)
    message = text_data_json['message']
    recipient_username = text_data_json['recipient']
    recipient = await self.get_user_by_username(username=recipient_username)
    
    if recipient is None:
        # existing error handling
        return
        
    if await self.is_blocked(recipient):  # Pass recipient
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': 'You cannot message this user due to a block.',
            'sender': self.user.username
        }))
        return
    # rest of the code
```

**Checklist:**

- [ ] is_blocked accepts recipient parameter
- [ ] Block check is bidirectional
- [ ] Unit test for specific block scenario
- [ ] Test: user can message non-blocked users

**Verification:** Create block A->B, verify A can message C, but not B---

### 2.2 Remove Duplicate Code

**Problem:** `TextbookListViewSet` and `TextbookViewSet` overlap; duplicate `IsAuthenticatedOrReadOnly`.File: `textbook_marketplace/marketplace/views.py`:

```python
from rest_framework.permissions import IsAuthenticatedOrReadOnly  # Use DRF's built-in

# Remove custom IsAuthenticatedOrReadOnly class

class TextbookViewSet(viewsets.ModelViewSet):
    """Unified ViewSet for all textbook operations."""
    queryset = Textbook.objects.all()
    serializer_class = TextbookSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filterset_class = TextbookFilter
    
    def perform_create(self, serializer):
        serializer.save(seller=self.request.user)
```

File: `textbook_marketplace/marketplace/urls.py`:

```python
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'textbooks', TextbookViewSet, basename='textbook')

urlpatterns = [
    path('', include(router.urls)),
    # other paths...
]
```

**Checklist:**

- [ ] Single TextbookViewSet handles all CRUD
- [ ] Custom IsAuthenticatedOrReadOnly removed
- [ ] URLs use router for consistency
- [ ] All existing tests pass

---

### 2.3 Add Database Indexes

File: `textbook_marketplace/marketplace/models.py`:

```python
class Textbook(models.Model):
    seller = models.ForeignKey(User, on_delete=models.CASCADE, 
                               related_name="textbooks", db_index=True)
    school_class = models.CharField(max_length=50, db_index=True)
    subject = models.CharField(max_length=255, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['price']),
            models.Index(fields=['condition']),
            models.Index(fields=['-created_at']),
        ]
```

**Checklist:**

- [ ] Index on seller FK
- [ ] Index on school_class, subject
- [ ] Index on created_at for sorting
- [ ] Migration created and applied

**Verification:** `EXPLAIN ANALYZE` on filter queries---

## Phase 3: Missing Core Features (Week 2-3)

### 3.1 Homepage Implementation

**Product Vision:** "Homepage displays latest textbooks in grid (4 in a row) with infinite scroll."**Frontend Changes:**File: `src/app/page.tsx`:

```typescript
import TextbookGridDataProvider from "@/components/TextbookGridDataProvider";
import SearchBar from "@/components/SearchBar";

export default function Home() {
  return (
    <div className="container mx-auto px-4 py-8">
      <section className="text-center mb-12">
        <h1 className="text-4xl font-bold mb-4">
          Find Affordable Textbooks
        </h1>
        <p className="text-lg text-gray-600 mb-8">
          Buy and sell used textbooks at great prices
        </p>
        <SearchBar />
      </section>
      
      <section>
        <h2 className="text-2xl font-bold mb-6">Latest Textbooks</h2>
        <TextbookGridDataProvider />
      </section>
    </div>
  );
}
```

**New Component:** `src/components/SearchBar.tsx`:

```typescript
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function SearchBar() {
  const [query, setQuery] = useState("");
  const router = useRouter();
  
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    router.push(`/textbooks?query=${encodeURIComponent(query)}`);
  };
  
  return (
    <form onSubmit={handleSearch} className="flex max-w-2xl mx-auto">
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search by title, author..."
        className="flex-1 px-4 py-3 border rounded-l-lg"
      />
      <button type="submit" className="px-6 py-3 bg-blue-600 text-white rounded-r-lg">
        Search
      </button>
    </form>
  );
}
```

**Checklist:**

- [ ] Homepage shows latest textbooks
- [ ] Search bar prominent on homepage
- [ ] Grid layout matches vision (4 columns desktop)
- [ ] Responsive design

---

### 3.2 Textbook Detail Page

**Product Vision:** "Shows photos, description, seller contact info, Message Seller button."**Backend:** Add endpoint for seller info (if needed).**Frontend Changes:**File: `src/app/textbook/[id]/page.tsx`:

```typescript
import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";
import TextbookService from "@/services/TextbookService";
import ContactButtons from "@/components/ContactButtons";
import MessageSellerButton from "@/components/MessageSellerButton";

export default async function TextbookDetail({ 
  params 
}: { 
  params: Promise<{ id: string }> 
}) {
  const { id } = await params;
  
  try {
    const response = await TextbookService.getTextbook(id);
    const textbook = response.data;
    
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="grid md:grid-cols-2 gap-8">
          {/* Image Section */}
          <div className="relative aspect-square">
            <Image
              src={textbook.image.full_size}
              alt={textbook.title}
              fill
              className="object-cover rounded-lg"
              priority
            />
          </div>
          
          {/* Details Section */}
          <div className="space-y-6">
            <div>
              <span className="px-3 py-1 bg-gray-200 rounded text-sm">
                {textbook.condition}
              </span>
              <h1 className="text-3xl font-bold mt-2">{textbook.title}</h1>
              <p className="text-gray-600">{textbook.author}</p>
            </div>
            
            <div className="text-3xl font-bold text-blue-600">
              {textbook.price} RSD
            </div>
            
            <div className="space-y-2">
              <p><strong>Grade:</strong> {textbook.school_class}</p>
              <p><strong>Publisher:</strong> {textbook.publisher}</p>
              <p><strong>Subject:</strong> {textbook.subject}</p>
            </div>
            
            <div>
              <h3 className="font-bold mb-2">Description</h3>
              <p className="text-gray-700">{textbook.description}</p>
            </div>
            
            <div className="border-t pt-6">
              <h3 className="font-bold mb-4">Contact Seller</h3>
              <div className="flex flex-wrap gap-3">
                <ContactButtons textbook={textbook} />
                <MessageSellerButton seller={textbook.seller} />
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  } catch {
    notFound();
  }
}
```

**New Component:** `src/components/ContactButtons.tsx`:

```typescript
import { TextbookType } from "@/utils/types";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faWhatsapp, faTelegram, faViber } from "@fortawesome/free-brands-svg-icons";
import { faPhone } from "@fortawesome/free-solid-svg-icons";

export default function ContactButtons({ textbook }: { textbook: TextbookType }) {
  const contacts = [
    { contact: textbook.whatsapp_contact, icon: faWhatsapp, label: "WhatsApp", 
      href: `https://wa.me/${textbook.whatsapp_contact}` },
    { contact: textbook.telegram_contact, icon: faTelegram, label: "Telegram",
      href: `https://t.me/${textbook.telegram_contact}` },
    { contact: textbook.viber_contact, icon: faViber, label: "Viber",
      href: `viber://chat?number=${textbook.viber_contact}` },
    { contact: textbook.phone_contact, icon: faPhone, label: "Phone",
      href: `tel:${textbook.phone_contact}` },
  ];
  
  return (
    <>
      {contacts.filter(c => c.contact).map(({ icon, label, href }) => (
        <a
          key={label}
          href={href}
          className="flex items-center gap-2 px-4 py-2 border rounded-lg hover:bg-gray-50"
          target="_blank"
          rel="noopener noreferrer"
        >
          <FontAwesomeIcon icon={icon} />
          {label}
        </a>
      ))}
    </>
  );
}
```

**Checklist:**

- [ ] Textbook detail page shows all info
- [ ] Image displayed properly
- [ ] External contact buttons work
- [ ] "Message Seller" button visible
- [ ] 404 for non-existent textbook
- [ ] Responsive layout

---

### 3.3 Chat/Messaging UI

**Backend:** WebSocket already implemented. Need message history endpoint.**Backend Addition:**File: `textbook_marketplace/chat/views.py`:

```python
class ConversationView(APIView):
    """Get message history with specific user."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, username):
        user = request.user
        other_user = get_object_or_404(User, username=username)
        messages = Message.objects.filter(
            Q(sender=user, recipient=other_user) |
            Q(sender=other_user, recipient=user)
        ).order_by('sent_at')
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)
```

**Frontend WebSocket Service:**File: `src/services/websocketService.ts`:

```typescript
type MessageHandler = (data: WebSocketMessage) => void;

interface WebSocketMessage {
  type: 'message' | 'error' | 'notification';
  message?: string;
  sender?: string;
  recipient?: string;
  new_messages?: Message[];
}

class WebSocketService {
  private ws: WebSocket | null = null;
  private handlers: MessageHandler[] = [];
  
  connect(token: string) {
    const wsUrl = `${process.env.NEXT_PUBLIC_WS_URL}/ws/chat/?token=${token}`;
    this.ws = new WebSocket(wsUrl);
    
    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handlers.forEach(handler => handler(data));
    };
    
    this.ws.onclose = () => {
      // Reconnect logic
      setTimeout(() => this.connect(token), 3000);
    };
  }
  
  sendMessage(recipient: string, message: string) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ recipient, message }));
    }
  }
  
  subscribe(handler: MessageHandler) {
    this.handlers.push(handler);
    return () => {
      this.handlers = this.handlers.filter(h => h !== handler);
    };
  }
  
  disconnect() {
    this.ws?.close();
  }
}

export default new WebSocketService();
```

**Frontend Chat Component:**File: `src/app/profile/messages/page.tsx`:

```typescript
"use client";

import { useEffect, useState } from "react";
import useUserStore from "@/hooks/useUserStore";
import websocketService from "@/services/websocketService";
import ChatSidebar from "@/components/Chat/ChatSidebar";
import ChatWindow from "@/components/Chat/ChatWindow";

interface Conversation {
  username: string;
  lastMessage: string;
  unread: number;
}

export default function Messages() {
  const { user } = useUserStore(state => state);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeChat, setActiveChat] = useState<string | null>(null);
  
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (token && user) {
      websocketService.connect(token);
      
      return () => websocketService.disconnect();
    }
  }, [user]);
  
  return (
    <section className="w-full h-[600px] bg-white rounded-xl shadow-md border flex">
      <ChatSidebar 
        conversations={conversations} 
        activeChat={activeChat}
        onSelectChat={setActiveChat}
      />
      {activeChat ? (
        <ChatWindow username={activeChat} />
      ) : (
        <div className="flex-1 flex items-center justify-center text-gray-500">
          Select a conversation
        </div>
      )}
    </section>
  );
}
```

**Checklist:**

- [ ] WebSocket service created
- [ ] Chat sidebar shows conversations
- [ ] Chat window shows message history
- [ ] Real-time message sending/receiving
- [ ] Unread message indicators
- [ ] Mark messages as read

---

### 3.4 User Profile Edit/Delete Listings

**Backend:** Add update/delete endpoints (if missing).File: `textbook_marketplace/marketplace/views.py`:

```python
class TextbookViewSet(viewsets.ModelViewSet):
    # ... existing code ...
    
    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsOwner()]
        return super().get_permissions()

class IsOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.seller == request.user
```

**Frontend - My Listings with Edit/Delete:**File: `src/components/TextbookGrid/UserTextbookCard.tsx`:

```typescript
"use client";

import { TextbookType } from "@/utils/types";
import Image from "next/image";
import Link from "next/link";
import { useState } from "react";
import TextbookService from "@/services/TextbookService";
import { useRouter } from "next/navigation";

export default function UserTextbookCard({ textbook }: { textbook: TextbookType }) {
  const [isDeleting, setIsDeleting] = useState(false);
  const router = useRouter();
  
  const handleDelete = async () => {
    if (!confirm("Are you sure you want to delete this listing?")) return;
    
    setIsDeleting(true);
    try {
      await TextbookService.deleteTextbook(String(textbook.id));
      router.refresh();
    } catch (error) {
      alert("Failed to delete listing");
    } finally {
      setIsDeleting(false);
    }
  };
  
  return (
    <div className="bg-white rounded-xl shadow border p-4">
      {/* Textbook info... */}
      <div className="flex gap-2 mt-4">
        <Link 
          href={`/profile/edit-listing/${textbook.id}`}
          className="px-4 py-2 bg-blue-500 text-white rounded"
        >
          Edit
        </Link>
        <button
          onClick={handleDelete}
          disabled={isDeleting}
          className="px-4 py-2 bg-red-500 text-white rounded disabled:opacity-50"
        >
          {isDeleting ? "Deleting..." : "Delete"}
        </button>
      </div>
    </div>
  );
}
```

**Checklist:**

- [ ] Edit button links to edit form
- [ ] Delete button with confirmation
- [ ] Only owner can edit/delete
- [ ] Optimistic UI updates

---

### 3.5 About/FAQ Page

File: `src/app/about/page.tsx`:

```typescript
export default function About() {
  const faqs = [
    {
      q: "How do I sell a textbook?",
      a: "Create an account, click 'Post Ad', fill in the details, and your textbook will be visible to all users."
    },
    {
      q: "Is posting ads free?",
      a: "Yes! Posting ads is completely free on SecondBook."
    },
    // ... more FAQs
  ];
  
  return (
    <div className="container mx-auto px-4 py-12 max-w-3xl">
      <h1 className="text-4xl font-bold mb-8">About SecondBook</h1>
      
      <section className="mb-12">
        <p className="text-lg text-gray-700 leading-relaxed">
          SecondBook is a platform for buying and selling used textbooks 
          at affordable prices in Belgrade. Connect with sellers directly 
          through our built-in chat or external contact methods.
        </p>
      </section>
      
      <section>
        <h2 className="text-2xl font-bold mb-6">Frequently Asked Questions</h2>
        <div className="space-y-4">
          {faqs.map((faq, i) => (
            <details key={i} className="border rounded-lg p-4">
              <summary className="font-medium cursor-pointer">{faq.q}</summary>
              <p className="mt-2 text-gray-600">{faq.a}</p>
            </details>
          ))}
        </div>
      </section>
    </div>
  );
}
```

**Checklist:**

- [ ] About page created
- [ ] FAQ section with expandable items
- [ ] Link in footer/navbar

---

### 3.6 404 Error Page

File: `src/app/not-found.tsx`:

```typescript
import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] px-4">
      <h1 className="text-6xl font-bold text-gray-300 mb-4">404</h1>
      <h2 className="text-2xl font-semibold mb-4">Page Not Found</h2>
      <p className="text-gray-600 mb-8 text-center">
        The page you're looking for doesn't exist or has been moved.
      </p>
      <Link 
        href="/"
        className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
      >
        Back to Home
      </Link>
    </div>
  );
}
```

**Checklist:**

- [ ] Custom 404 page created
- [ ] Friendly design
- [ ] Link back to homepage

---

## Phase 4: UX Improvements (Week 3-4)

### 4.1 Loading States

**Create reusable loading components:**File: `src/components/Skeleton/TextbookCardSkeleton.tsx`:

```typescript
export default function TextbookCardSkeleton() {
  return (
    <div className="bg-white rounded-xl shadow border animate-pulse">
      <div className="aspect-square bg-gray-200 rounded-t-xl" />
      <div className="p-4 space-y-3">
        <div className="h-4 bg-gray-200 rounded w-1/4" />
        <div className="h-6 bg-gray-200 rounded w-3/4" />
        <div className="h-4 bg-gray-200 rounded w-1/2" />
      </div>
    </div>
  );
}
```

**Apply to data-fetching components:**

```typescript
// In TextbookGridDataProvider
const [isLoading, setIsLoading] = useState(true);

if (isLoading) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {Array.from({ length: 8 }).map((_, i) => (
        <TextbookCardSkeleton key={i} />
      ))}
    </div>
  );
}
```

**Checklist:**

- [ ] Skeleton components created
- [ ] Loading states on all async operations
- [ ] Smooth transitions

---

### 4.2 Error Handling & Toast Notifications

**Library:** `react-hot-toast`**Add to package.json:**

```json
"react-hot-toast": "^2.4.1"
```

**Setup:**File: `src/app/layout.tsx`:

```typescript
import { Toaster } from 'react-hot-toast';

// In return:
<Toaster position="top-right" />
```

**Usage:**

```typescript
import toast from 'react-hot-toast';

// On success
toast.success('Textbook posted successfully!');

// On error
toast.error('Failed to post textbook. Please try again.');
```

**Checklist:**

- [ ] Toast library installed
- [ ] Success/error toasts on all actions
- [ ] Consistent error messages

---

### 4.3 Pagination UI

File: `src/components/Pagination.tsx`:

```typescript
interface PaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

export default function Pagination({ currentPage, totalPages, onPageChange }: PaginationProps) {
  return (
    <div className="flex justify-center gap-2 mt-8">
      <button
        onClick={() => onPageChange(currentPage - 1)}
        disabled={currentPage === 1}
        className="px-4 py-2 border rounded disabled:opacity-50"
      >
        Previous
      </button>
      
      {Array.from({ length: totalPages }, (_, i) => i + 1).map(page => (
        <button
          key={page}
          onClick={() => onPageChange(page)}
          className={`px-4 py-2 border rounded ${
            page === currentPage ? 'bg-blue-600 text-white' : ''
          }`}
        >
          {page}
        </button>
      ))}
      
      <button
        onClick={() => onPageChange(currentPage + 1)}
        disabled={currentPage === totalPages}
        className="px-4 py-2 border rounded disabled:opacity-50"
      >
        Next
      </button>
    </div>
  );
}
```

**Checklist:**

- [ ] Pagination component created
- [ ] Integrated with textbook list
- [ ] URL query params for page state

---

### 4.4 Image Upload with Preview

File: `src/components/ImageUpload.tsx`:

```typescript
"use client";

import { useState, useRef } from "react";
import Image from "next/image";

interface ImageUploadProps {
  name: string;
  onChange?: (file: File | null) => void;
}

export default function ImageUpload({ name, onChange }: ImageUploadProps) {
  const [preview, setPreview] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreview(reader.result as string);
      };
      reader.readAsDataURL(file);
      onChange?.(file);
    }
  };
  
  return (
    <div className="space-y-4">
      <input
        ref={inputRef}
        type="file"
        name={name}
        accept="image/*"
        onChange={handleChange}
        className="hidden"
      />
      
      {preview ? (
        <div className="relative w-48 h-48">
          <Image src={preview} alt="Preview" fill className="object-cover rounded" />
          <button
            type="button"
            onClick={() => {
              setPreview(null);
              if (inputRef.current) inputRef.current.value = '';
              onChange?.(null);
            }}
            className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full w-6 h-6"
          >
            x
          </button>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="w-48 h-48 border-2 border-dashed rounded flex items-center justify-center text-gray-400"
        >
          Click to upload
        </button>
      )}
    </div>
  );
}
```

**Checklist:**

- [ ] Image preview before upload
- [ ] Remove image button
- [ ] File type validation
- [ ] Size limit indicator

---

## Phase 5: Testing (Week 4-5)

### 5.1 Frontend Unit Tests

**Setup:**

```bash
pnpm add -D jest @testing-library/react @testing-library/jest-dom jest-environment-jsdom
```

**Config:** `jest.config.js`:

```javascript
const nextJest = require('next/jest');

const createJestConfig = nextJest({ dir: './' });

module.exports = createJestConfig({
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
  },
});
```

**Example Test:** `src/components/__tests__/TextbookCard.test.tsx`:

```typescript
import { render, screen } from '@testing-library/react';
import TextbookCard from '../TextbookCard/TextbookCard';

const mockTextbook = {
  id: 1,
  title: 'Test Book',
  author: 'Test Author',
  price: '100',
  condition: 'New',
  // ... other fields
};

describe('TextbookCard', () => {
  it('renders textbook information', () => {
    render(<TextbookCard textbook={mockTextbook} index={0} />);
    
    expect(screen.getByText('Test Book')).toBeInTheDocument();
    expect(screen.getByText('Test Author')).toBeInTheDocument();
    expect(screen.getByText('100')).toBeInTheDocument();
  });
});
```

**Checklist:**

- [ ] Jest configured
- [ ] Tests for key components
- [ ] Tests for hooks
- [ ] Tests for services

---

### 5.2 E2E Tests with Playwright

**Setup:**

```bash
pnpm add -D @playwright/test
npx playwright install
```

**Config:** `playwright.config.ts`:

```typescript
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  baseURL: 'http://localhost:3000',
  use: {
    trace: 'on-first-retry',
  },
});
```

**Example Test:** `e2e/textbook-flow.spec.ts`:

```typescript
import { test, expect } from '@playwright/test';

test.describe('Textbook Flow', () => {
  test('user can view textbook list', async ({ page }) => {
    await page.goto('/textbooks');
    await expect(page.locator('h1')).toContainText('Textbooks');
    await expect(page.locator('[data-testid="textbook-card"]').first()).toBeVisible();
  });

  test('user can view textbook detail', async ({ page }) => {
    await page.goto('/textbooks');
    await page.locator('[data-testid="textbook-card"]').first().click();
    await expect(page.url()).toContain('/textbook/');
  });
});
```

**Checklist:**

- [ ] Playwright configured
- [ ] E2E tests for critical flows
- [ ] CI integration

---

## Phase 6: Documentation & DevOps (Week 5-6)

### 6.1 API Documentation with drf-spectacular

**Setup:**

```toml
# pyproject.toml
"drf-spectacular==0.27.1",
```

**Config:** `settings.py`:

```python
INSTALLED_APPS = [
    # ...
    'drf_spectacular',
]

REST_FRAMEWORK = {
    # ...
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'SecondBook API',
    'DESCRIPTION': 'Textbook marketplace API',
    'VERSION': '1.0.0',
}
```

**URLs:**

```python
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
```

**Checklist:**

- [ ] drf-spectacular installed
- [ ] Swagger UI available at /api/docs/
- [ ] All endpoints documented

---

### 6.2 Structured Logging

**Library:** `structlog`

```python
# settings.py
import structlog

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': structlog.stdlib.ProcessorFormatter,
            'processor': structlog.processors.JSONRenderer(),
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}
```

**Usage:**

```python
import structlog
logger = structlog.get_logger()

logger.info("textbook_created", textbook_id=textbook.id, seller=request.user.username)
```

**Checklist:**

- [ ] structlog configured
- [ ] JSON logging for production
- [ ] Key events logged

---

## Summary Checklist

### Security (Phase 1)

- [ ] DEBUG=False in production
- [ ] CORS properly configured
- [ ] Password validators enabled
- [ ] Rate limiting on auth endpoints
- [ ] Input validation and sanitization
- [ ] UserSerializer uses safe fields
- [ ] SSR-safe token handling

### Bug Fixes (Phase 2)

- [ ] WebSocket block logic fixed
- [ ] Duplicate code removed
- [ ] Database indexes added

### Features (Phase 3)

- [ ] Homepage with search bar
- [ ] Textbook detail page complete
- [ ] Chat/messaging UI working
- [ ] Edit/delete listings
- [ ] About/FAQ page
- [ ] 404 page

### UX (Phase 4)

- [ ] Loading skeletons
- [ ] Toast notifications
- [ ] Pagination UI
- [ ] Image upload preview

### Testing (Phase 5)

- [ ] Frontend unit tests
- [ ] E2E tests with Playwright

### Documentation (Phase 6)

- [ ] Swagger API docs
- [ ] Structured logging

---

## Verification Methods

| Feature | Test Method ||---------|-------------|| Security config | `python manage.py check --deploy` || Rate limiting | Rapid API calls with curl || Input validation | Submit invalid data via API || WebSocket block | Create block, test messaging || Frontend pages | Visual inspection + E2E tests || Chat | Send messages between users || CRUD operations | API tests + UI testing || Loading states | Throttle network in DevTools || Error handling | Trigger errors intentionally |---

## Estimated Timeline

| Phase | Duration | Priority ||-------|----------|----------|| Phase 1: Security | 1 week | Critical || Phase 2: Bug Fixes | 0.5 week | Critical || Phase 3: Features | 2 weeks | High || Phase 4: UX | 1 week | Medium || Phase 5: Testing | 1 week | High |