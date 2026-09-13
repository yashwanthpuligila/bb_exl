"""
Product Recommendation Engine
Uses collaborative filtering and association rules for product recommendations
"""

import pandas as pd
import numpy as np
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from openpyxl import load_workbook
import glob
import os
from itertools import combinations
import json


class ProductRecommendationEngine:
    """ML-based product recommendation system"""
    
    def __init__(self):
        self.customer_products = defaultdict(list)  # customer -> [products]
        self.product_cooccurrence = defaultdict(lambda: defaultdict(int))  # product -> {related_product: count}
        self.product_popularity = Counter()  # product -> purchase count
        self.customer_history = defaultdict(list)  # customer -> [(product, quantity, price, date)]
        
    def clear_data(self):
        """Reset and wipe all in-memory learned customer and product recommendation caches"""
        self.customer_products.clear()
        self.product_cooccurrence.clear()
        self.product_popularity.clear()
        self.customer_history.clear()
        print("🧹 Recommendation engine caches cleared.")
        
    def rebuild_from_db(self):
        """Rebuild collaborative filtering caches directly from SQLite database"""
        self.clear_data()
        try:
            import learning_db
            with learning_db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT i.customer_norm, ii.product_display, ii.quantity, ii.price, i.invoice_date, ii.invoice_number
                    FROM invoice_items ii
                    JOIN invoices i ON ii.invoice_number = i.invoice_number
                    ORDER BY i.invoice_date ASC
                """)
                rows = cursor.fetchall()
                
                inv_products = defaultdict(list)
                for c_norm, p_name, qty, price, inv_date, inv_num in rows:
                    clean_prod = " ".join(str(p_name).strip().split())
                    self.customer_products[c_norm].append(clean_prod)
                    self.product_popularity[clean_prod] += 1
                    self.customer_history[c_norm].append((clean_prod, qty, price, inv_date))
                    inv_products[inv_num].append(clean_prod)
                
                # Build co-occurrence matrix from each invoice's products
                for prods in inv_products.values():
                    unique_prods = list(set(prods))
                    if len(unique_prods) >= 2:
                        for p1, p2 in combinations(unique_prods, 2):
                            self.product_cooccurrence[p1][p2] += 1
                            self.product_cooccurrence[p2][p1] += 1
            print(f"🤖 Recommendation engine re-synced from DB ({len(self.customer_products)} customers, {len(self.product_popularity)} products)")
            return True
        except Exception as e:
            print(f"Error rebuilding recommendations from DB: {e}")
            return False
        
    def load_data_from_invoices(self, invoice_directory='.'):
        """Load historical data from all invoice Excel files"""
        try:
            # Find all invoice files (supporting both flat directories and customer subfolders)
            invoice_files = []
            for root, _, files in os.walk(invoice_directory):
                for f in files:
                    if f.endswith('.xlsx') and not f.startswith('~$') and ('Invoice' in f or 'INV' in f):
                        invoice_files.append(os.path.join(root, f))
            
            if not invoice_files:
                print("No invoice files found for training")
                return False
            
            print(f"📊 Loading data from {len(invoice_files)} invoice files...")
            
            for invoice_file in invoice_files:
                try:
                    # Extract customer name from folder or filename
                    filename = os.path.basename(invoice_file)
                    parent_name = os.path.basename(os.path.dirname(invoice_file))
                    if parent_name and parent_name not in ['.', 'web', 'Invoice Storage', os.path.basename(invoice_directory)]:
                        customer_name = parent_name
                    elif filename.startswith('Invoice_'):
                        customer_name = filename.replace('Invoice_', '').split('_')[0]
                    else:
                        customer_name = filename.split('.')[0]
                    
                    # Load workbook
                    wb = load_workbook(invoice_file, data_only=True)
                    ws = wb.active
                    
                    # Extract products from invoice
                    products_in_order = []
                    current_order_products = []
                    
                    for row in ws.iter_rows(min_row=1, values_only=True):
                        # Look for product rows (has Description, Qty, Unit Price, Total Price)
                        if row[0] and isinstance(row[0], str) and len(row) >= 4:
                            # Skip headers
                            if row[0] in ['Description', 'Shop:', 'Owner:', 'Area:', 'Contact:']:
                                continue
                            
                            # Check if this is a product row (has numeric quantity and price)
                            if row[1] and row[2] and isinstance(row[1], (int, float)) and isinstance(row[2], (int, float)):
                                product_name = str(row[0]).strip()
                                quantity = float(row[1])
                                price = float(row[2])
                                
                                if product_name and quantity > 0 and price >= 0:
                                    products_in_order.append(product_name)
                                    current_order_products.append(product_name)
                                    self.customer_history[customer_name].append({
                                        'product': product_name,
                                        'quantity': quantity,
                                        'price': price,
                                        'timestamp': datetime.now()  # Would be better to extract from file
                                    })
                        
                        # Detect new order separator
                        if row[0] and isinstance(row[0], str) and 'NEW ORDER' in str(row[0]):
                            if current_order_products:
                                self._process_order(customer_name, current_order_products)
                                current_order_products = []
                    
                    # Process last order
                    if current_order_products:
                        self._process_order(customer_name, current_order_products)
                    
                    # Also process all products together for this customer
                    if products_in_order:
                        self.customer_products[customer_name].extend(products_in_order)
                        
                except Exception as e:
                    print(f"Error processing {invoice_file}: {str(e)}")
                    continue
            
            print(f"✅ Loaded data for {len(self.customer_products)} customers")
            print(f"✅ Found {len(self.product_popularity)} unique products")
            
            return True
            
        except Exception as e:
            print(f"Error loading invoice data: {str(e)}")
            return False
    
    def _process_order(self, customer_name, products):
        """Process a single order for association rules"""
        # Update product popularity
        for product in products:
            self.product_popularity[product] += 1
        
        # Update product co-occurrence (products bought together)
        for prod1, prod2 in combinations(set(products), 2):
            self.product_cooccurrence[prod1][prod2] += 1
            self.product_cooccurrence[prod2][prod1] += 1
    
    def get_recommendations(self, customer_name=None, current_products=None, method='hybrid', top_n=5):
        """
        Get product recommendations
        
        Args:
            customer_name: Customer name for personalized recommendations
            current_products: List of products currently in cart
            method: 'collaborative', 'association', 'popularity', or 'hybrid'
            top_n: Number of recommendations to return
            
        Returns:
            List of recommended products with scores
        """
        recommendations = []
        
        if method in ['collaborative', 'hybrid'] and customer_name:
            recommendations.extend(self._collaborative_filtering(customer_name))
        
        if method in ['association', 'hybrid'] and current_products:
            recommendations.extend(self._association_rules(current_products))
        
        if method in ['popularity', 'hybrid']:
            recommendations.extend(self._popularity_based())
        
        # Remove duplicates and already purchased/in cart products
        exclude_products = set()
        if current_products:
            exclude_products.update(current_products)
        if customer_name and customer_name in self.customer_products:
            # Don't completely exclude previously purchased, but de-prioritize
            pass
        
        # Score and rank recommendations
        product_scores = defaultdict(float)
        for product, score, source in recommendations:
            if product not in exclude_products:
                product_scores[product] += score
        
        # Sort by score and return top N
        sorted_recommendations = sorted(
            product_scores.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:top_n]
        
        # Format output with reasoning
        result = []
        for product, score in sorted_recommendations:
            result.append({
                'product': product,
                'confidence': min(score / 10, 1.0),  # Normalize to 0-1
                'reason': self._get_recommendation_reason(product, customer_name, current_products)
            })
        
        return result
    
    def _collaborative_filtering(self, customer_name):
        """Recommend based on similar customers' purchases"""
        recommendations = []
        
        if customer_name not in self.customer_products:
            return recommendations
        
        customer_products_set = set(self.customer_products[customer_name])
        
        # Find similar customers (those who bought similar products)
        similar_customers = []
        for other_customer, other_products in self.customer_products.items():
            if other_customer != customer_name:
                other_products_set = set(other_products)
                # Calculate Jaccard similarity
                intersection = len(customer_products_set & other_products_set)
                union = len(customer_products_set | other_products_set)
                if union > 0:
                    similarity = intersection / union
                    if similarity > 0.1:  # At least 10% similarity
                        similar_customers.append((other_customer, similarity, other_products_set))
        
        # Recommend products from similar customers
        product_scores = Counter()
        for other_customer, similarity, other_products in similar_customers:
            for product in other_products:
                if product not in customer_products_set:
                    product_scores[product] += similarity * 5  # Weight by similarity
        
        for product, score in product_scores.items():
            recommendations.append((product, score, 'collaborative'))
        
        return recommendations
    
    def _association_rules(self, current_products):
        """Recommend based on products frequently bought together"""
        recommendations = []
        
        product_scores = Counter()
        for product in current_products:
            if product in self.product_cooccurrence:
                for related_product, count in self.product_cooccurrence[product].items():
                    if related_product not in current_products:
                        # Calculate confidence score
                        support = count / max(self.product_popularity[product], 1)
                        product_scores[related_product] += support * 10
        
        for product, score in product_scores.items():
            recommendations.append((product, score, 'association'))
        
        return recommendations
    
    def _popularity_based(self):
        """Recommend popular products"""
        recommendations = []
        
        for product, count in self.product_popularity.most_common(10):
            score = count / max(sum(self.product_popularity.values()), 1) * 3
            recommendations.append((product, score, 'popularity'))
        
        return recommendations
    
    def _get_recommendation_reason(self, product, customer_name, current_products):
        """Generate human-readable reason for recommendation"""
        reasons = []
        
        # Check if frequently bought together
        if current_products:
            for cart_product in current_products:
                if cart_product in self.product_cooccurrence:
                    if product in self.product_cooccurrence[cart_product]:
                        count = self.product_cooccurrence[cart_product][product]
                        reasons.append(f"Often bought with {cart_product}")
                        break
        
        # Check popularity
        if product in self.product_popularity:
            count = self.product_popularity[product]
            if count >= 3:
                reasons.append(f"Popular item ({count} purchases)")
        
        # Check if similar customers bought it
        if customer_name and customer_name in self.customer_products:
            customer_products_set = set(self.customer_products[customer_name])
            for other_customer, other_products in self.customer_products.items():
                if other_customer != customer_name:
                    other_products_set = set(other_products)
                    if product in other_products_set:
                        intersection = len(customer_products_set & other_products_set)
                        if intersection >= 2:
                            reasons.append("Similar customers bought this")
                            break
        
        return reasons[0] if reasons else "Recommended for you"
    
    def get_customer_insights(self, customer_name):
        """Get insights about a specific customer"""
        if customer_name not in self.customer_products:
            return None
        
        customer_prods = self.customer_products[customer_name]
        history = self.customer_history[customer_name]
        
        # Calculate statistics
        total_purchases = len(customer_prods)
        unique_products = len(set(customer_prods))
        
        # Most purchased products
        product_counts = Counter(customer_prods)
        favorite_products = product_counts.most_common(5)
        
        # Average order value
        total_spent = sum(item['quantity'] * item['price'] for item in history)
        avg_order_value = total_spent / len(set(item['product'] for item in history)) if history else 0
        
        return {
            'customer_name': customer_name,
            'total_purchases': total_purchases,
            'unique_products': unique_products,
            'favorite_products': [{'product': p, 'count': c} for p, c in favorite_products],
            'total_spent': round(total_spent, 2),
            'avg_order_value': round(avg_order_value, 2)
        }
    
    def get_trending_products(self, days=30, top_n=10):
        """Get trending products based on recent purchases"""
        # For now, return most popular (would need date tracking for true trending)
        trending = [
            {
                'product': product,
                'purchase_count': count,
                'trend': 'up'  # Would calculate based on time series
            }
            for product, count in self.product_popularity.most_common(top_n)
        ]
        return trending


# Global instance
recommendation_engine = ProductRecommendationEngine()
