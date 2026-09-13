# 🏗️ ML System Architecture

## 📊 System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     USER INTERFACE (Browser)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Customer    │  │  Product     │  │  AI          │          │
│  │  Info Form   │  │  Cart        │  │  Suggestions │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│           │               │                    │                 │
└───────────┼───────────────┼────────────────────┼─────────────────┘
            │               │                    │
            ▼               ▼                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                   FLASK API SERVER (Python)                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  API Endpoints                                            │  │
│  │  • POST /api/generate-invoice                            │  │
│  │  • POST /api/recommendations      ◄─── ML POWERED       │  │
│  │  • GET  /api/customer-insights/<name>                    │  │
│  │  • GET  /api/trending-products                           │  │
│  └──────────────────────────────────────────────────────────┘  │
│           │               │                    │                 │
└───────────┼───────────────┼────────────────────┼─────────────────┘
            │               │                    │
            ▼               ▼                    ▼
┌─────────────────────────────────────────────────────────────────┐
│              ML RECOMMENDATION ENGINE (Python)                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  recommendation_engine.py                                 │  │
│  │                                                            │  │
│  │  ┌─────────────────┐  ┌──────────────────┐              │  │
│  │  │ Collaborative   │  │ Association      │              │  │
│  │  │ Filtering       │  │ Rules Mining     │              │  │
│  │  │                 │  │                  │              │  │
│  │  │ Find similar    │  │ Find products    │              │  │
│  │  │ customers       │  │ bought together  │              │  │
│  │  └─────────────────┘  └──────────────────┘              │  │
│  │           │                     │                         │  │
│  │           └──────────┬──────────┘                         │  │
│  │                      │                                    │  │
│  │           ┌──────────▼──────────┐                         │  │
│  │           │  Hybrid Scoring     │                         │  │
│  │           │  & Ranking          │                         │  │
│  │           └──────────┬──────────┘                         │  │
│  │                      │                                    │  │
│  │           ┌──────────▼──────────┐                         │  │
│  │           │ Confidence          │                         │  │
│  │           │ Calculation         │                         │  │
│  │           └─────────────────────┘                         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                         │                                       │
└─────────────────────────┼───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                   DATA LAYER (Excel Files)                       │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐               │
│  │ Invoice_   │  │ Invoice_   │  │ Invoice_   │  ...           │
│  │ customer1  │  │ customer2  │  │ customer3  │                │
│  │ .xlsx      │  │ .xlsx      │  │ .xlsx      │                │
│  └────────────┘  └────────────┘  └────────────┘               │
│                                                                  │
│  Contains: Customer, Products, Quantities, Prices, Dates        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Data Flow

### **1. Startup Sequence**
```
Server Start
    │
    ├─► Load Flask App
    │
    ├─► Initialize Recommendation Engine
    │
    ├─► Scan for Invoice_*.xlsx files
    │
    ├─► Extract Historical Data
    │        │
    │        ├─► Customer → Products mapping
    │        ├─► Product co-occurrence matrix
    │        └─► Product popularity counts
    │
    └─► Ready to serve requests
```

### **2. User Interaction Flow**
```
User enters customer name
    │
    ▼
JavaScript: customerNameInput.blur event
    │
    ├─► Call /api/customer-insights/<name>
    │        │
    │        ├─► Query customer history
    │        ├─► Calculate statistics
    │        └─► Return insights JSON
    │
    └─► Display customer dashboard
            (purchases, spend, favorites)
```

### **3. Recommendation Flow**
```
User adds product to cart
    │
    ▼
JavaScript: addProduct() function
    │
    ├─► Update products array
    ├─► Update UI
    │
    └─► Call loadRecommendations()
            │
            ▼
    POST /api/recommendations
            │
            ├─── Input: {
            │      customerName: "John",
            │      currentProducts: ["Coffee"],
            │      method: "hybrid",
            │      topN: 6
            │    }
            │
            ▼
    ML Engine processes:
            │
            ├─► Collaborative Filtering
            │       │
            │       ├─► Find similar customers
            │       ├─► Get their products
            │       └─► Score × 5
            │
            ├─► Association Rules
            │       │
            │       ├─► Check co-occurrence matrix
            │       ├─► Calculate confidence
            │       └─► Score × 10
            │
            ├─► Popularity
            │       │
            │       ├─► Get popular products
            │       └─► Score × 3
            │
            ├─► Combine scores
            ├─► Rank by total score
            ├─► Take top N
            └─► Calculate confidence (0-1)
            │
            ▼
    Return: [
      {
        product: "Sugar",
        confidence: 0.85,
        reason: "Often bought with Coffee"
      },
      ...
    ]
            │
            ▼
    JavaScript: displayRecommendations()
            │
            ├─► Create recommendation cards
            ├─► Show confidence bars
            ├─► Add click handlers
            └─► Render to DOM
```

### **4. Invoice Generation Flow**
```
User clicks "Generate Invoice"
    │
    ▼
POST /api/generate-invoice
    │
    ├─► Validate customer data
    ├─► Validate products
    │
    ├─► Check for existing invoice file
    │       │
    │       ├─► If exists: Append to file
    │       └─► If new: Create new file
    │
    ├─► Format Excel with OpenPyXL
    │       │
    │       ├─► Headers, styling, borders
    │       ├─► Add products and totals
    │       └─► Calculate grand total
    │
    ├─► Save to disk
    │
    └─► Return download URL
            │
            ▼
    Browser downloads .xlsx file
            │
            └─► Data available for next ML training
```

---

## 🧠 ML Algorithm Details

### **Collaborative Filtering**
```python
def _collaborative_filtering(customer_name):
    # 1. Get customer's products
    customer_products = set(self.customer_products[customer_name])
    
    # 2. Find similar customers
    for other_customer, other_products in all_customers:
        other_set = set(other_products)
        
        # 3. Calculate Jaccard similarity
        intersection = len(customer_products & other_set)
        union = len(customer_products | other_set)
        similarity = intersection / union
        
        # 4. If similar enough (>10%)
        if similarity > 0.1:
            # 5. Recommend their products
            for product in other_set:
                if product not in customer_products:
                    score = similarity × 5
                    recommendations.add(product, score)
    
    return recommendations
```

### **Association Rules**
```python
def _association_rules(current_products):
    # 1. For each product in cart
    for product in current_products:
        
        # 2. Check co-occurrence matrix
        related_products = self.product_cooccurrence[product]
        
        # 3. For each related product
        for related, count in related_products.items():
            
            # 4. Calculate confidence
            support = count / max(self.product_popularity[product], 1)
            score = support × 10
            
            # 5. Add recommendation
            recommendations.add(related, score)
    
    return recommendations
```

### **Hybrid Scoring**
```python
def get_recommendations(customer, cart, method='hybrid'):
    recommendations = []
    
    # Collect from all methods
    if method == 'hybrid':
        recommendations += collaborative_filtering(customer)
        recommendations += association_rules(cart)
        recommendations += popularity_based()
    
    # Aggregate scores
    product_scores = {}
    for product, score, source in recommendations:
        product_scores[product] += score
    
    # Rank and return top N
    sorted_recs = sorted(product_scores.items(), 
                        key=lambda x: x[1], 
                        reverse=True)[:top_n]
    
    # Normalize confidence (0-1)
    for product, score in sorted_recs:
        confidence = min(score / 10, 1.0)
        result.append({
            'product': product,
            'confidence': confidence,
            'reason': get_reason(product)
        })
    
    return result
```

---

## 📦 Technology Stack

### **Frontend**
- **HTML5**: Semantic structure
- **CSS3**: Modern gradients, animations, flexbox, grid
- **JavaScript ES6+**: Async/await, fetch API, arrow functions

### **Backend**
- **Flask**: Lightweight web framework
- **Flask-CORS**: Cross-origin resource sharing

### **ML & Data**
- **Pandas**: Data manipulation
- **NumPy**: Numerical computing
- **Collections**: Counter, defaultdict
- **Scikit-learn**: (ready for future expansion)

### **File Processing**
- **OpenPyXL**: Excel file creation and reading

---

## 🔒 Security & Performance

### **Security**
- CORS enabled for browser safety
- Input validation on all endpoints
- No SQL injection risk (Excel files only)
- Local data storage (no external APIs)

### **Performance**
- In-memory data structures for speed
- O(n) complexity for most operations
- Lazy loading of recommendations
- Caching via Flask's request cycle

### **Scalability**
- Current: Handles ~1000 invoices easily
- Bottleneck: Excel file parsing
- Future: Could add database (SQLite, PostgreSQL)

---

## 🎯 Key Design Decisions

### **Why Hybrid Recommendations?**
- Single methods have limitations
- Hybrid combines strengths
- Fallback when data is sparse
- More accurate overall

### **Why Excel Files?**
- User's existing format
- Easy to backup and share
- No database setup needed
- Business-friendly format

### **Why In-Memory?**
- Fast recommendations (<100ms)
- Simple architecture
- Sufficient for typical use
- Can upgrade to DB later

### **Why Flask?**
- Lightweight and simple
- Perfect for small-medium projects
- Easy to deploy
- Python ecosystem integration

---

## 📈 Future Architecture

### **Phase 2: Database Integration**
```
Excel Files → Python Script → PostgreSQL → Flask → Browser
                  (ETL)
```

### **Phase 3: Real-time Learning**
```
User Action → Event Queue → ML Model Update → Redis Cache → API
```

### **Phase 4: Microservices**
```
┌──────────┐    ┌──────────┐    ┌──────────┐
│ Frontend │───►│   API    │───►│   ML     │
│ Service  │    │ Gateway  │    │ Service  │
└──────────┘    └──────────┘    └──────────┘
                      │              │
                      ▼              ▼
                ┌──────────┐    ┌──────────┐
                │   DB     │    │  Cache   │
                │ Service  │    │ Service  │
                └──────────┘    └──────────┘
```

---

**Built with ❤️ using Python ML + Modern Web Technologies**
