// Global variables
let products = [];
let invoiceCounter = 1;

// DOM elements
const shopNameInput = document.getElementById('shopName');
const areaInput = document.getElementById('area');
const productNameInput = document.getElementById('productName');
const quantityInput = document.getElementById('quantity');
const priceInput = document.getElementById('price');
const addProductBtn = document.getElementById('addProductBtn');
const productsList = document.getElementById('productsList');
const totalAmount = document.getElementById('totalAmount');
const clearAllBtn = document.getElementById('clearAllBtn');
const generateInvoiceBtn = document.getElementById('generateInvoiceBtn');
const statusMessage = document.getElementById('statusMessage');
const loadingOverlay = document.getElementById('loadingOverlay');

// Event listeners
document.addEventListener('DOMContentLoaded', function() {
    addProductBtn.addEventListener('click', addProduct);
    clearAllBtn.addEventListener('click', clearAll);
    generateInvoiceBtn.addEventListener('click', generateInvoice);
    
    // Set Header Current Date
    const dateHeaderEl = document.getElementById('currentDateHeader');
    if (dateHeaderEl) {
        const now = new Date();
        dateHeaderEl.textContent = now.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' });
    }
    
    // Load system stats
    loadSystemStats();
    
    // Auto-refresh stats every 30 seconds
    setInterval(loadSystemStats, 30000);
    
    // Customer Recommendations event listeners
    const refreshRecommendationsBtn = document.getElementById('refreshRecommendationsBtn');
    if (refreshRecommendationsBtn) {
        refreshRecommendationsBtn.addEventListener('click', () => {
            const name = shopNameInput.value.trim();
            loadCustomerRecommendations(name, true);
        });
    }
    
    // Immediately load recommendations when typing or changing Shop Name
    shopNameInput.addEventListener('input', debounce(function() {
        const query = this.value.trim();
        if (query.length >= 2) {
            loadCustomerRecommendations(query);
        } else if (!query) {
            const recSection = document.getElementById('recommendationsSection');
            if (recSection) recSection.style.display = 'none';
        }
    }, 350));
    
    shopNameInput.addEventListener('change', function() {
        const query = this.value.trim();
        if (query) {
            loadCustomerRecommendations(query);
        }
    });
    
    // Initialize customer and product autocomplete system
    initAutocomplete();
    
    // Live price calculation
    quantityInput.addEventListener('input', updateLiveTotal);
    priceInput.addEventListener('input', updateLiveTotal);
    
    // Enter key support for product form
    [productNameInput, quantityInput, priceInput].forEach(input => {
        input.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                addProduct();
            }
        });
    });
    
    // Auto-focus next field
    shopNameInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') areaInput.focus();
    });
    
    areaInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') productNameInput.focus();
    });

    // Invoice Modal event listeners
    const modalPrintBtn = document.getElementById('modalPrintBtn');
    if (modalPrintBtn) modalPrintBtn.addEventListener('click', printInvoice);

    const modalWhatsAppBtn = document.getElementById('modalWhatsAppBtn');
    if (modalWhatsAppBtn) modalWhatsAppBtn.addEventListener('click', shareViaWhatsApp);

    const modalExcelBtn = document.getElementById('modalExcelBtn');
    if (modalExcelBtn) modalExcelBtn.addEventListener('click', downloadCurrentExcel);

    const modalNewTabBtn = document.getElementById('modalNewTabBtn');
    if (modalNewTabBtn) modalNewTabBtn.addEventListener('click', openStandaloneInvoice);

    const modalCloseBtn = document.getElementById('modalCloseBtn');
    if (modalCloseBtn) modalCloseBtn.addEventListener('click', closeInvoiceModal);

    const modalOverlay = document.getElementById('modalOverlay');
    if (modalOverlay) modalOverlay.addEventListener('click', closeInvoiceModal);

    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') closeInvoiceModal();
    });
});

// Add product function
function addProduct() {
    const productName = productNameInput.value.trim();
    const quantity = parseInt(quantityInput.value);
    const price = parseFloat(priceInput.value);
    
    // Validation
    if (!productName) {
        showStatus('Please enter product name', 'error');
        productNameInput.focus();
        return;
    }
    
    if (!quantity || quantity <= 0) {
        showStatus('Please enter valid quantity', 'error');
        quantityInput.focus();
        return;
    }
    
    if (!price || price < 0) {
        showStatus('Please enter valid price', 'error');
        priceInput.focus();
        return;
    }
    
    // Calculate total
    const total = quantity * price;
    
    // Create product object
    const product = {
        id: Date.now(),
        name: productName,
        quantity: quantity,
        price: price,
        total: total
    };
    
    // Add to products array
    products.push(product);
    
    // Clear form
    productNameInput.value = '';
    quantityInput.value = '';
    priceInput.value = '';
    productNameInput.focus();
    
    // Update display
    updateProductsList();
    updateTotal();
    
    // Load recommendations after adding product
    loadRecommendations();
    
    showStatus(`Added: ${productName}`, 'success');
}

// Update products list display
function updateProductsList() {
    if (products.length === 0) {
        productsList.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📦</div>
                <div class="empty-title">No products added yet.</div>
                <div class="empty-sub">Add products above.</div>
            </div>`;
        return;
    }
    
    productsList.innerHTML = `
        <div class="table-responsive">
            <table class="products-table">
                <thead>
                    <tr>
                        <th class="col-num-header">#</th>
                        <th>Product Name</th>
                        <th class="text-center">Qty</th>
                        <th class="text-right">Unit Price</th>
                        <th class="text-right">Total</th>
                        <th class="text-center">Action</th>
                    </tr>
                </thead>
                <tbody>
                    ${products.map((product, index) => `
                        <tr class="product-row-item">
                            <td class="col-num">${index + 1}</td>
                            <td class="col-name"><span class="product-name-text">${product.name}</span></td>
                            <td class="col-qty text-center"><span class="qty-pill">${product.quantity}</span></td>
                            <td class="col-price text-right">₹${product.price.toFixed(2)}</td>
                            <td class="col-total text-right"><span class="item-total-price">₹${product.total.toFixed(2)}</span></td>
                            <td class="col-action text-center">
                                <button type="button" class="btn-table-delete" onclick="removeProduct(${product.id})" title="Remove product">
                                    🗑️
                                </button>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;
}

// Remove product function
function removeProduct(productId) {
    products = products.filter(product => product.id !== productId);
    updateProductsList();
    updateTotal();
    showStatus('Product removed', 'info');
}

// Update total amount
function updateTotal() {
    const total = products.reduce((sum, product) => sum + product.total, 0);
    totalAmount.textContent = `₹${total.toFixed(2)}`;
}

// Clear all function
function clearAll() {
    if (products.length === 0) {
        showStatus('No products to clear', 'info');
        return;
    }
    
    if (confirm('Are you sure you want to clear all products?')) {
        products = [];
        updateProductsList();
        updateTotal();
        showStatus('All products cleared', 'info');
        productNameInput.focus();
    }
}

// State for currently generated invoice
let currentInvoiceData = null;
let currentHistoryData = null;
let currentExcelDownloadUrl = null;

// Escape HTML utility
function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// Indian currency number formatter with standard grouping
function formatIndianCurrency(num) {
    if (num === null || num === undefined || isNaN(num)) return "0.00";
    return Number(num).toLocaleString('en-IN', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

// Amount to Indian currency words converter (Crore, Lakh, Thousand, Rupees, Paise)
function numberToIndianWords(num) {
    if (isNaN(num) || num === 0) return "Zero Rupees Only";
    
    const ones = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten',
                  'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen'];
    const tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety'];
    
    function twoDigits(n) {
        if (n < 20) return ones[n];
        return (tens[Math.floor(n / 10)] + (n % 10 ? ' ' + ones[n % 10] : '')).trim();
    }
    
    function threeDigits(n) {
        let s = '';
        if (Math.floor(n / 100) > 0) {
            s += ones[Math.floor(n / 100)] + ' Hundred';
            if (n % 100 > 0) s += ' and ';
        }
        if (n % 100 > 0) s += twoDigits(n % 100);
        return s.trim();
    }
    
    const parts = Number(num).toFixed(2).split('.');
    let integ = parseInt(parts[0], 10);
    const dec = parseInt(parts[1], 10);
    
    if (integ === 0 && dec === 0) return 'Zero Rupees Only';
    
    const cr = Math.floor(integ / 10000000);
    integ %= 10000000;
    const la = Math.floor(integ / 100000);
    integ %= 100000;
    const th = Math.floor(integ / 1000);
    integ %= 1000;
    const rem = integ;
    
    const res = [];
    if (cr) res.push(twoDigits(cr) + ' Crore');
    if (la) res.push(twoDigits(la) + ' Lakh');
    if (th) res.push(twoDigits(th) + ' Thousand');
    if (rem) res.push(threeDigits(rem));
    
    let out = res.join(' ').trim() + ' Rupees';
    if (dec > 0) {
        out += ' and ' + twoDigits(dec) + ' Paise';
    }
    return out + ' Only';
}

// Generate invoice function
async function generateInvoice() {
    // Validate customer information
    const shopName = shopNameInput.value.trim();
    const area = areaInput.value.trim();
    
    if (!shopName) {
        showStatus('Please enter shop name', 'error');
        shopNameInput.focus();
        return;
    }
    
    if (!area) {
        showStatus('Please enter area', 'error');
        areaInput.focus();
        return;
    }
    
    if (products.length === 0) {
        showStatus('Please add at least one product', 'error');
        productNameInput.focus();
        return;
    }
    
    showLoading(true);
    
    try {
        const invoiceType = document.querySelector('input[name="invoiceType"]:checked').value;
        const now = new Date();
        const formattedDate = now.toLocaleDateString('en-IN', {
            day: '2-digit',
            month: 'short',
            year: 'numeric'
        });
        
        const invoiceData = {
            customer: {
                shopName: shopName,
                area: area
            },
            products: JSON.parse(JSON.stringify(products)),
            invoiceNumber: generateInvoiceNumber(),
            date: formattedDate,
            total: products.reduce((sum, p) => sum + p.total, 0),
            invoiceType: invoiceType
        };
        
        // Call backend API to create Excel record and fetch history
        const result = await generateExcelInvoice(invoiceData);
        
        if (result && result.success) {
            if (result.invoice_number) {
                invoiceData.invoiceNumber = result.invoice_number;
            }
            
            // Cache current invoice state for modal actions
            currentInvoiceData = invoiceData;
            currentHistoryData = result.history || {};
            currentExcelDownloadUrl = result.download_url;
            
            // Render and display the professional A4 Indian Wholesale Tax Invoice
            displayInvoiceModal(invoiceData, result.history || {}, result.download_url);
            
            showToast('Tax Invoice generated successfully!', 'success', 3000);
            showStatus('Invoice generated successfully! You can now Print / Save as PDF or Share on WhatsApp.', 'success');
            
            // Refresh customer recommendations immediately with the updated order history
            loadCustomerRecommendations(shopName);
        } else {
            throw new Error((result && result.error) || 'Failed to generate invoice');
        }
    } catch (error) {
        console.error('Error generating invoice:', error);
        showStatus('Error generating invoice: ' + error.message, 'error');
        showToast('Error generating invoice', 'error');
    } finally {
        showLoading(false);
    }
}

// Generate invoice number
function generateInvoiceNumber() {
    const now = new Date();
    const dateStr = now.toISOString().slice(0, 10).replace(/-/g, '');
    const timeStr = now.toTimeString().slice(0, 5).replace(':', '');
    return `INV-${dateStr}-${timeStr}-${invoiceCounter++}`;
}

// Generate Excel invoice using Flask backend API
async function generateExcelInvoice(invoiceData) {
    try {
        const response = await fetch('/api/generate-invoice', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(invoiceData)
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to generate invoice');
        }
        
        return await response.json();
    } catch (error) {
        console.error('Error:', error);
        throw error;
    }
}

// Render complete Indian Wholesale Tax Invoice HTML
function renderInvoiceHTML(invoiceData, historyData) {
    const customer = invoiceData.customer || {};
    const products = invoiceData.products || [];
    const isHistory = (invoiceData.invoiceType === 'all') &&
                      historyData &&
                      historyData.previous_orders &&
                      historyData.previous_orders.length > 0;
                      
    const currentTotal = products.reduce((sum, p) => sum + (Number(p.total) || 0), 0);
    const totalQty = products.reduce((sum, p) => sum + (Number(p.quantity) || 0), 0);
    
    let prevTotal = 0;
    if (isHistory) {
        prevTotal = historyData.previous_orders.reduce((sum, ord) => sum + (Number(ord.total) || 0), 0);
    }
    
    const finalGrandTotal = isHistory ? (historyData.grand_total || (prevTotal + currentTotal)) : currentTotal;
    const amountInWords = numberToIndianWords(finalGrandTotal);
    
    // Product rows
    const productRowsHtml = products.map((p, idx) => `
        <tr>
            <td class="td-sno">${idx + 1}</td>
            <td class="td-desc">${escapeHtml(p.name)}</td>
            <td class="td-qty text-center">${p.quantity}</td>
            <td class="td-rate text-right">₹${formatIndianCurrency(p.price)}</td>
            <td class="td-amount text-right">₹${formatIndianCurrency(p.total)}</td>
        </tr>
    `).join('');
    
    // Previous orders table for statement/history
    let historyHtml = '';
    if (isHistory) {
        historyHtml = `
            <div class="history-section-box">
                <div class="history-header-bar">
                    📜 PREVIOUS ORDERS HISTORY (ACCOUNT STATEMENT)
                </div>
                <table class="history-table">
                    <thead>
                        <tr>
                            <th style="width: 60px; text-align: center;">Order #</th>
                            <th style="width: 140px;">Order Date</th>
                            <th>Description / Reference</th>
                            <th style="width: 140px;" class="text-right">Amount (₹)</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${historyData.previous_orders.map((ord, idx) => `
                            <tr>
                                <td style="text-align: center; font-weight: 600;">#${ord.order_number || idx + 1}</td>
                                <td>${escapeHtml(ord.date)}</td>
                                <td style="color: #64748B;">Wholesale Order Billing</td>
                                <td style="text-align: right; font-weight: 600;">₹${formatIndianCurrency(ord.total)}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                    <tfoot>
                        <tr class="history-tfoot">
                            <td colspan="3" style="text-align: right;">Previous Orders Total (${historyData.previous_orders.length} orders):</td>
                            <td style="text-align: right; color: #1E1B4B; font-weight: 800;">₹${formatIndianCurrency(prevTotal)}</td>
                        </tr>
                    </tfoot>
                </table>
            </div>
        `;
    }
    
    return `
        <div class="tax-invoice-wrapper" id="taxInvoice">
            <div class="invoice-box">
                
                <!-- Invoice Header -->
                <div class="invoice-top-header">
                    <div class="company-header-left">
                        <div class="company-logo-area">
                            <div class="logo-box">
                                <span class="logo-letters">SLG</span>
                                <span class="logo-sub">TRADERS</span>
                            </div>
                            <div class="company-title-block">
                                <div class="company-title">SRI LAXMI GAYATRI TRADERS</div>
                                <div class="company-subtitle">WHOLESALE DISTRIBUTORS & GENERAL MERCHANTS</div>
                                <div class="company-contact">
                                    <span><strong>Phone:</strong> +91 94403 67824</span>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="invoice-meta-right">
                        <div class="doc-badge-heading">TAX INVOICE</div>
                        <table class="invoice-meta-table">
                            <tr>
                                <td class="lbl">Invoice No:</td>
                                <td class="val inv-number-highlight">${escapeHtml(invoiceData.invoiceNumber)}</td>
                            </tr>
                            <tr>
                                <td class="lbl">Date:</td>
                                <td class="val">${escapeHtml(invoiceData.date)}</td>
                            </tr>
                            <tr>
                                <td class="lbl">Bill Type:</td>
                                <td class="val">
                                    <span class="bill-type-tag">${isHistory ? 'All Bills (With History)' : 'Current Bill Only'}</span>
                                </td>
                            </tr>
                            <tr>
                                <td class="lbl">Place of Supply:</td>
                                <td class="val">Telangana (36)</td>
                            </tr>
                        </table>
                    </div>
                </div>

                <!-- Buyer / Bill To Section -->
                <div class="customer-section-box">
                    <div class="section-bar">
                        BILL TO / BUYER DETAILS
                    </div>
                    <div class="customer-content-grid">
                        <div class="cust-col">
                            <div class="cust-row">
                                <span class="cust-lbl">Shop Name:</span>
                                <span class="cust-val shop-name-bold">${escapeHtml(customer.shopName)}</span>
                            </div>
                            <div class="cust-row">
                                <span class="cust-lbl">Area / Location:</span>
                                <span class="cust-val">${escapeHtml(customer.area)}</span>
                            </div>
                        </div>
                        <div class="cust-col">
                            <div class="cust-row">
                                <span class="cust-lbl">State:</span>
                                <span class="cust-val">Telangana (Code: 36)</span>
                            </div>
                            <div class="cust-row">
                                <span class="cust-lbl">Payment Mode:</span>
                                <span class="cust-val">Cash / Credit (Wholesale)</span>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- History Orders Table if applicable -->
                ${historyHtml}

                <!-- Current Order Items Table -->
                <div class="items-table-wrapper">
                    ${isHistory ? '<div class="table-subheading">🛍️ CURRENT ORDER (TODAY\'S INVOICE)</div>' : ''}
                    <table class="items-table">
                        <thead>
                            <tr>
                                <th class="th-sno">S.No.</th>
                                <th class="th-desc">Description of Goods</th>
                                <th class="th-qty text-center">Qty</th>
                                <th class="th-rate text-right">Unit Price (₹)</th>
                                <th class="th-amount text-right">Amount (₹)</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${productRowsHtml}
                        </tbody>
                        <tfoot>
                            <tr class="tfoot-subtotal">
                                <td colspan="2" class="text-left font-semibold">
                                    Total Items: <strong>${products.length}</strong>
                                </td>
                                <td class="text-center font-bold qty-highlight">${totalQty}</td>
                                <td class="text-right font-semibold">Current Order Total:</td>
                                <td class="text-right font-bold amount-highlight">₹${formatIndianCurrency(currentTotal)}</td>
                            </tr>
                        </tfoot>
                    </table>
                </div>

                <!-- Bottom Financial Summary Block -->
                <div class="bottom-financial-grid invoice-summary no-break">
                    <div class="fin-left-col">
                        <div class="amount-words-container">
                            <div class="amount-words-title">Amount Chargeable (in words):</div>
                            <div class="amount-words-content">INR ${amountInWords}</div>
                        </div>
                    </div>

                    <div class="fin-right-col">
                        <table class="totals-table">
                            <tr>
                                <td class="t-lbl">Current Order Total:</td>
                                <td class="t-val">₹${formatIndianCurrency(currentTotal)}</td>
                            </tr>
                            ${isHistory ? `
                            <tr>
                                <td class="t-lbl">Previous Orders (${historyData.previous_orders.length} orders):</td>
                                <td class="t-val">₹${formatIndianCurrency(prevTotal)}</td>
                            </tr>
                            ` : ''}
                            <tr class="grand-total-row">
                                <td class="gt-lbl">${isHistory ? 'CUMULATIVE GRAND TOTAL:' : 'GRAND TOTAL:'}</td>
                                <td class="gt-val">₹${formatIndianCurrency(finalGrandTotal)}</td>
                            </tr>
                        </table>
                        ${isHistory ? `
                        <div class="history-stat-pills">
                            <span>Total Orders: <strong>${(historyData.previous_orders.length + 1)}</strong></span>
                            <span>Latest: <strong>${escapeHtml(invoiceData.date)}</strong></span>
                        </div>
                        ` : ''}
                    </div>
                </div>

                <!-- Signatures Section -->
                <div class="footer-sign-section invoice-footer no-break">
                    <div class="signature-columns">
                        <div class="sign-block customer-sign-block">
                            <div class="sign-space"></div>
                            <div class="sign-line">Customer's Signature</div>
                        </div>
                        <div class="sign-block company-sign-block">
                            <div class="sign-company-name">For SRI LAXMI GAYATRI TRADERS</div>
                            <div class="sign-space"></div>
                            <div class="sign-line">Authorised Signatory</div>
                        </div>
                    </div>
                </div>

            </div>
        </div>
    `;
}

// Display modal with generated invoice
function displayInvoiceModal(invoiceData, historyData, downloadUrl) {
    const modal = document.getElementById('invoiceModal');
    const printArea = document.getElementById('invoicePrintArea');
    const invNumEl = document.getElementById('modalInvoiceNumber');
    const typeTagEl = document.getElementById('modalInvoiceTypeTag');
    
    if (invNumEl) invNumEl.textContent = invoiceData.invoiceNumber;
    if (typeTagEl) {
        typeTagEl.textContent = invoiceData.invoiceType === 'all' ? 'All Bills (With History)' : 'Current Bill Only';
    }
    
    const invoiceHtml = renderInvoiceHTML(invoiceData, historyData);
    if (printArea) {
        printArea.innerHTML = invoiceHtml;
    }
    
    if (modal) {
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
}

// Close invoice modal
function closeInvoiceModal() {
    const modal = document.getElementById('invoiceModal');
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = '';
    }
}

// Print invoice reliably using browser's native window.print()
async function printInvoice() {
    const modal = document.getElementById('invoiceModal');
    const printArea = document.getElementById('invoicePrintArea');
    
    if (!modal || !modal.classList.contains('active') || !printArea || !printArea.children.length) {
        showToast('Please generate an invoice before printing', 'warning');
        return;
    }

    // Wait until fonts and resources are fully ready before launching print dialog
    if (document.fonts && document.fonts.ready) {
        try {
            await document.fonts.ready;
        } catch (e) {
            console.warn('Font loading check completed with warning:', e);
        }
    }

    // Wait for DOM layout and rendering to settle
    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            setTimeout(() => {
                window.print();
            }, 60);
        });
    });
}

// WhatsApp Share
function shareViaWhatsApp() {
    if (!currentInvoiceData) return;
    const isHistory = (currentInvoiceData.invoiceType === 'all') && 
                      currentHistoryData && 
                      currentHistoryData.previous_orders && 
                      currentHistoryData.previous_orders.length > 0;
    const finalGrandTotal = isHistory ? (currentHistoryData.grand_total || currentInvoiceData.total) : currentInvoiceData.total;
    
    const shop = currentInvoiceData.customer.shopName;
    const invNo = currentInvoiceData.invoiceNumber;
    const date = currentInvoiceData.date;
    const productsList = currentInvoiceData.products;
    
    let text = `*TAX INVOICE - SRI LAXMI GAYATRI TRADERS*\n`;
    text += `*Invoice No:* ${invNo}\n`;
    text += `*Date:* ${date}\n`;
    text += `*Bill To:* ${shop} (${currentInvoiceData.customer.area})\n`;
    text += `--------------------------------\n`;
    text += `*PARTICULARS:*\n`;
    productsList.forEach((p, i) => {
        text += `${i + 1}. ${p.name} - ${p.quantity} x ₹${formatIndianCurrency(p.price)} = ₹${formatIndianCurrency(p.total)}\n`;
    });
    text += `--------------------------------\n`;
    if (isHistory) {
        text += `*Current Order Total:* ₹${formatIndianCurrency(currentInvoiceData.total)}\n`;
        text += `*CUMULATIVE GRAND TOTAL:* ₹${formatIndianCurrency(finalGrandTotal)}\n`;
    } else {
        text += `*GRAND TOTAL:* ₹${formatIndianCurrency(finalGrandTotal)}\n`;
    }
    text += `*Amount in Words:* ${numberToIndianWords(finalGrandTotal)}\n`;
    text += `--------------------------------\n`;
    text += `Thank you for your business!\n`;
    text += `Sri Laxmi Gayatri Traders, Hyderabad\n`;
    text += `Phone: +91 94403 67824`;
    
    const url = `https://api.whatsapp.com/send?text=${encodeURIComponent(text)}`;
    window.open(url, '_blank');
}

// Download Excel file
function downloadCurrentExcel() {
    if (!currentExcelDownloadUrl) {
        showToast('No Excel file available for download', 'warning');
        return;
    }
    const a = document.createElement('a');
    a.href = currentExcelDownloadUrl;
    a.download = currentExcelDownloadUrl.split('/').pop();
    a.target = '_blank';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    showToast('Downloading Excel file...', 'info', 2000);
}

// Open invoice in standalone window/tab
function openStandaloneInvoice() {
    if (!currentInvoiceData) return;
    const invoiceHtml = renderInvoiceHTML(currentInvoiceData, currentHistoryData);
    const newWin = window.open('', '_blank');
    if (!newWin) {
        showToast('Please allow popups to open invoice in new tab', 'warning');
        return;
    }
    
    const fullHtml = `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tax Invoice - ${escapeHtml(currentInvoiceData.customer.shopName)}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Noto+Sans+Devanagari:wght@400;600;700&family=Noto+Sans+Telugu:wght@400;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="styles.css">
    <style>
        body {
            background: #475569;
            margin: 0;
            padding: 24px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .standalone-toolbar {
            background: #1E1B4B;
            color: #FFFFFF;
            padding: 12px 24px;
            border-radius: 10px;
            margin-bottom: 24px;
            display: flex;
            align-items: center;
            gap: 14px;
            box-shadow: 0 4px 14px rgba(0,0,0,0.25);
        }
        .btn-tab-action {
            background: #4F46E5;
            color: #FFF;
            border: none;
            padding: 8px 18px;
            border-radius: 6px;
            font-weight: 700;
            cursor: pointer;
            font-family: inherit;
        }
        .btn-tab-action:hover { background: #4338CA; }
        @media print {
            body { background: #FFF !important; padding: 0 !important; }
            .standalone-toolbar { display: none !important; }
        }
    </style>
</head>
<body>
    <div class="standalone-toolbar">
        <span>📄 Invoice #${escapeHtml(currentInvoiceData.invoiceNumber)}</span>
        <button class="btn-tab-action" onclick="window.print()">🖨️ Print / Save as PDF</button>
    </div>
    <div class="invoice-sheet-container">
        ${invoiceHtml}
    </div>
</body>
</html>`;

    newWin.document.open();
    newWin.document.write(fullHtml);
    newWin.document.close();
}

// Reset form function
function resetForm() {
    shopNameInput.value = '';
    areaInput.value = '';
    productNameInput.value = '';
    quantityInput.value = '';
    priceInput.value = '';
    products = [];
    updateProductsList();
    updateTotal();
    hideStatus();
    shopNameInput.focus();
}

// Show status message
function showStatus(message, type) {
    statusMessage.textContent = message;
    statusMessage.className = `status-message ${type}`;
    statusMessage.style.display = 'block';
    
    // Auto-hide after 3 seconds for success/info messages
    if (type === 'success' || type === 'info') {
        setTimeout(hideStatus, 3000);
    }
}

// Hide status message
function hideStatus() {
    statusMessage.style.display = 'none';
}

// Show/hide loading overlay
function showLoading(show) {
    loadingOverlay.style.display = show ? 'flex' : 'none';
}

// Auto-save to localStorage (optional)
function saveToLocalStorage() {
    const data = {
        customer: {
            shopName: shopNameInput.value,
            area: areaInput.value
        },
        products: products
    };
    localStorage.setItem('invoiceData', JSON.stringify(data));
}

// Load from localStorage (optional)
function loadFromLocalStorage() {
    const data = localStorage.getItem('invoiceData');
    if (data) {
        try {
            const parsedData = JSON.parse(data);
            shopNameInput.value = parsedData.customer.shopName || '';
            areaInput.value = parsedData.customer.area || '';
            products = parsedData.products || [];
            updateProductsList();
            updateTotal();
        } catch (e) {
            console.error('Error loading from localStorage:', e);
        }
    }
}

// Save data periodically
setInterval(saveToLocalStorage, 10000); // Save every 10 seconds

// Load data on page load
// loadFromLocalStorage();

// ==================== CUSTOMER-SPECIFIC RECOMMENDATION FUNCTIONS ====================

// Load customer-specific product recommendations based on their own order history
async function loadCustomerRecommendations(shopName, forceRefresh = false) {
    const recommendationsSection = document.getElementById('recommendationsSection');
    const recommendationsList = document.getElementById('recommendationsList');
    const titleEl = document.getElementById('recommendationsTitle');
    const descEl = document.getElementById('recommendationsDesc');

    if (!recommendationsSection || !recommendationsList) return;

    const trimmedName = (shopName || shopNameInput.value || '').trim();

    if (!trimmedName) {
        recommendationsSection.style.display = 'none';
        return;
    }

    recommendationsSection.style.display = 'block';
    if (titleEl) titleEl.textContent = `Frequently Ordered by ${trimmedName}`;
    if (descEl) descEl.textContent = 'Based on previous order history for this customer';

    recommendationsList.innerHTML = `
        <div class="loading-recommendations">
            <span class="loading-spinner">⏳</span> Fetching purchase history for <strong>${escapeHtml(trimmedName)}</strong>...
        </div>
    `;

    try {
        if (forceRefresh) {
            await fetch('/api/reload-recommendations', { method: 'POST' });
        }

        const response = await fetch(`/api/customer-recommendations?shopName=${encodeURIComponent(trimmedName)}&limit=8`);
        if (!response.ok) throw new Error('Failed to load customer recommendations');
        const data = await response.json();

        if (data.success && data.hasHistory && data.recommendations && data.recommendations.length > 0) {
            displayCustomerRecommendations(data);
        } else {
            displayEmptyCustomerRecommendations(data, trimmedName);
        }
    } catch (err) {
        console.error('Error loading customer recommendations:', err);
        recommendationsList.innerHTML = `
            <div class="rec-empty-state">
                <div class="rec-empty-icon">⚠️</div>
                <div class="rec-empty-text">Unable to load recommendations</div>
                <div class="rec-empty-sub">${escapeHtml(err.message || 'Please check your connection and try again.')}</div>
            </div>
        `;
    }
}

// Display customer recommendations cards
function displayCustomerRecommendations(data) {
    const recommendationsList = document.getElementById('recommendationsList');
    const titleEl = document.getElementById('recommendationsTitle');
    const descEl = document.getElementById('recommendationsDesc');

    const customerName = data.customer || shopNameInput.value.trim();
    if (titleEl) titleEl.textContent = `Frequently Ordered by ${customerName}`;
    if (descEl) descEl.textContent = `${data.recommendations.length} frequently purchased product${data.recommendations.length === 1 ? '' : 's'} based on previous invoices`;

    const html = data.recommendations.map((rec) => {
        const lastPriceFormatted = Number(rec.lastPrice).toFixed(2);
        const lastBoughtHtml = rec.lastOrderedRelative ? `
            <div class="rec-detail-row">
                <span class="rec-detail-label">Last Bought:</span>
                <span class="rec-detail-val">${escapeHtml(rec.lastOrderedRelative)}</span>
            </div>
        ` : '';

        return `
            <div class="customer-rec-card">
                <div class="rec-card-header">
                    <div class="rec-card-title-row">
                        <span class="rec-card-icon">🛍️</span>
                        <span class="rec-card-name" title="${escapeHtml(rec.product)}">${escapeHtml(rec.product)}</span>
                    </div>
                    <span class="rec-count-badge">Ordered ${rec.orderCount} ${rec.orderCount === 1 ? 'time' : 'times'}</span>
                </div>
                
                <div class="rec-card-body">
                    <div class="rec-detail-row">
                        <span class="rec-detail-label">Last Price:</span>
                        <span class="rec-detail-price">₹${lastPriceFormatted}</span>
                    </div>
                    <div class="rec-detail-row">
                        <span class="rec-detail-label">Total Qty:</span>
                        <span class="rec-detail-val">${rec.totalQuantity} units</span>
                    </div>
                    ${lastBoughtHtml}
                </div>
                
                <div class="rec-card-footer">
                    <button type="button" class="btn btn-select-rec" onclick="selectRecommendedProduct('${rec.product.replace(/'/g, "\\'")}', ${rec.lastPrice})">
                        <span class="btn-icon">➕</span> Select Product
                    </button>
                </div>
            </div>
        `;
    }).join('');

    recommendationsList.innerHTML = html;
}

// Display empty history state with optional popular products
function displayEmptyCustomerRecommendations(data, customerName) {
    const recommendationsList = document.getElementById('recommendationsList');
    const titleEl = document.getElementById('recommendationsTitle');
    const descEl = document.getElementById('recommendationsDesc');

    if (titleEl) titleEl.textContent = `Frequently Ordered by ${customerName}`;
    if (descEl) descEl.textContent = 'Customer purchase history';

    let popularHtml = '';
    if (data.popularProducts && data.popularProducts.length > 0) {
        const cards = data.popularProducts.map(p => `
            <div class="popular-card">
                <div class="popular-card-title">${escapeHtml(p.product)}</div>
                <div class="popular-card-details">
                    <span class="popular-card-price">₹${Number(p.lastPrice).toFixed(2)}</span>
                    <span class="popular-card-count">${p.usageCount} orders</span>
                </div>
                <button type="button" class="btn btn-select-rec" style="padding: 5px 8px; font-size: 0.78rem;" onclick="selectRecommendedProduct('${p.product.replace(/'/g, "\\'")}', ${p.lastPrice})">
                    ➕ Select
                </button>
            </div>
        `).join('');

        popularHtml = `
            <div class="popular-section">
                <div class="popular-header">
                    <span class="popular-icon">🔥</span>
                    <span class="popular-title">Popular Products in Store</span>
                    <span class="popular-badge">Store-Wide</span>
                </div>
                <div class="popular-grid">
                    ${cards}
                </div>
            </div>
        `;
    }

    recommendationsList.innerHTML = `
        <div class="rec-empty-state">
            <div class="rec-empty-icon">📦</div>
            <div class="rec-empty-text">No previous purchases found for this customer.</div>
            <div class="rec-empty-sub">Once you generate an invoice for <strong>${escapeHtml(customerName)}</strong>, their frequently ordered items will appear here automatically.</div>
        </div>
        ${popularHtml}
    `;
}

// Select recommended product: fills product name and last customer price, leaves quantity and price editable, focuses quantity, does NOT auto-add.
function selectRecommendedProduct(productName, price) {
    productNameInput.value = productName;
    if (price !== undefined && price !== null && Number(price) > 0) {
        priceInput.value = Number(price).toFixed(2);
    }
    updateLiveTotal();
    quantityInput.focus();
    
    // Smoothly scroll to product form for easy entry
    const productForm = document.querySelector('.product-form');
    if (productForm) {
        productForm.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    
    showToast(`Selected: ${productName} (Last price: ₹${Number(price).toFixed(2)})`, 'info', 2000);
}

// Load customer insights
async function loadCustomerInsights(customerName) {
    const insightsSection = document.getElementById('insightsSection');
    const customerInsights = document.getElementById('customerInsights');
    
    if (!customerName) {
        insightsSection.style.display = 'none';
        return;
    }
    
    try {
        const response = await fetch(`/api/customer-insights/${encodeURIComponent(customerName)}`);
        
        if (!response.ok) {
            throw new Error('Failed to load customer insights');
        }
        
        const data = await response.json();
        
        if (data.success && data.insights) {
            displayCustomerInsights(data.insights);
            insightsSection.style.display = 'block';
        } else {
            insightsSection.style.display = 'none';
        }
        
    } catch (error) {
        console.error('Error loading customer insights:', error);
        insightsSection.style.display = 'none';
    }
}

// Display customer insights
function displayCustomerInsights(insights) {
    const customerInsights = document.getElementById('customerInsights');
    
    const favoriteProducts = insights.favorite_products
        .map(p => `<span class="insight-badge">${p.product} (${p.count}×)</span>`)
        .join(' ');
    
    const html = `
        <div class="insights-grid">
            <div class="insight-card">
                <div class="insight-icon">🛒</div>
                <div class="insight-value">${insights.total_purchases}</div>
                <div class="insight-label">Total Purchases</div>
            </div>
            <div class="insight-card">
                <div class="insight-icon">📦</div>
                <div class="insight-value">${insights.unique_products}</div>
                <div class="insight-label">Unique Products</div>
            </div>
            <div class="insight-card">
                <div class="insight-icon">💰</div>
                <div class="insight-value">₹${insights.total_spent.toFixed(2)}</div>
                <div class="insight-label">Total Spent</div>
            </div>
            <div class="insight-card">
                <div class="insight-icon">📊</div>
                <div class="insight-value">₹${insights.avg_order_value.toFixed(2)}</div>
                <div class="insight-label">Avg Order Value</div>
            </div>
        </div>
        ${favoriteProducts ? `
            <div class="favorite-products">
                <h4>⭐ Favorite Products</h4>
                <div class="favorite-products-list">${favoriteProducts}</div>
            </div>
        ` : ''}
    `;
    
    customerInsights.innerHTML = html;
}

// ==================== DYNAMIC UI FEATURES ====================

// Debounce function for performance
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func.apply(this, args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Load system statistics
async function loadSystemStats() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();
        
        if (data.success) {
            animateCounter('totalCustomers', data.stats.total_customers);
            animateCounter('totalProducts', data.stats.total_products);
            animateCounter('totalOrders', data.stats.total_orders);
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Animate counter with easing
function animateCounter(elementId, targetValue) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    const startValue = parseInt(element.textContent) || 0;
    const duration = 1000;
    const startTime = performance.now();
    
    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        // Ease out cubic
        const easeProgress = 1 - Math.pow(1 - progress, 3);
        const currentValue = Math.floor(startValue + (targetValue - startValue) * easeProgress);
        
        element.textContent = currentValue;
        
        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }
    
    requestAnimationFrame(update);
}

// Utility: escape HTML to prevent XSS injection
function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// Generic reusable autocomplete controller supporting debounce, mouse, and keyboard navigation
function setupAutocomplete({
    inputEl,
    dropdownEl,
    fetchUrl,
    dataKey,
    renderItem,
    onSelect
}) {
    if (!inputEl || !dropdownEl) return;

    let items = [];
    let activeIndex = -1;
    let currentFetchId = 0;

    function hide() {
        dropdownEl.style.display = 'none';
        dropdownEl.innerHTML = '';
        items = [];
        activeIndex = -1;
    }

    function setActive(index) {
        activeIndex = index;
        const domItems = dropdownEl.querySelectorAll('.autocomplete-item');
        domItems.forEach((el, idx) => {
            if (idx === activeIndex) {
                el.classList.add('active');
                el.scrollIntoView({ block: 'nearest' });
            } else {
                el.classList.remove('active');
            }
        });
    }

    function render(newItems) {
        items = newItems;
        activeIndex = -1;
        if (!items || items.length === 0) {
            hide();
            return;
        }

        dropdownEl.innerHTML = items.map((item, idx) => renderItem(item, idx)).join('');
        dropdownEl.style.display = 'block';

        dropdownEl.querySelectorAll('.autocomplete-item').forEach((el, idx) => {
            el.addEventListener('mousedown', (e) => {
                // Use mousedown so selection happens before input blur
                e.preventDefault();
                e.stopPropagation();
                selectItem(idx);
            });
            el.addEventListener('mouseenter', () => {
                setActive(idx);
            });
        });
    }

    function selectItem(index) {
        if (index >= 0 && index < items.length) {
            const selected = items[index];
            hide();
            onSelect(selected);
        }
    }

    const debouncedFetch = debounce(async (query) => {
        if (!query) {
            hide();
            return;
        }
        const fetchId = ++currentFetchId;
        try {
            const res = await fetch(`${fetchUrl}${encodeURIComponent(query)}`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            if (fetchId !== currentFetchId) return; // Stale request
            if (data.success && Array.isArray(data[dataKey])) {
                render(data[dataKey]);
            } else {
                hide();
            }
        } catch (err) {
            console.error('Autocomplete fetch error:', err);
            hide();
        }
    }, 200);

    inputEl.addEventListener('input', function() {
        const query = this.value.trim();
        if (query.length < 1) {
            hide();
            return;
        }
        debouncedFetch(query);
    });

    inputEl.addEventListener('keydown', function(e) {
        const isOpen = dropdownEl.style.display === 'block' && items.length > 0;
        if (!isOpen) return;

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            const nextIndex = activeIndex < items.length - 1 ? activeIndex + 1 : 0;
            setActive(nextIndex);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            const prevIndex = activeIndex > 0 ? activeIndex - 1 : items.length - 1;
            setActive(prevIndex);
        } else if (e.key === 'Enter') {
            if (activeIndex >= 0 && activeIndex < items.length) {
                e.preventDefault();
                e.stopPropagation();
                selectItem(activeIndex);
            }
        } else if (e.key === 'Escape') {
            e.preventDefault();
            hide();
        }
    });

    // Close on click outside
    document.addEventListener('click', function(e) {
        if (!inputEl.contains(e.target) && !dropdownEl.contains(e.target)) {
            hide();
        }
    });

    return { hide };
}

// Initialize autocomplete for both Customer (Shop Name) and Product Name
function initAutocomplete() {
    // 1. Customer Autocomplete
    const customerDropdown = document.getElementById('customerAutocomplete');
    if (shopNameInput && customerDropdown) {
        setupAutocomplete({
            inputEl: shopNameInput,
            dropdownEl: customerDropdown,
            fetchUrl: '/api/autocomplete/customers?q=',
            dataKey: 'customers',
            renderItem: (cust, idx) => `
                <div class="autocomplete-item" data-index="${idx}">
                    <div class="autocomplete-info">
                        <span class="autocomplete-name">${escapeHtml(cust.shopName)}</span>
                        <span class="autocomplete-sep">—</span>
                        <span class="autocomplete-detail">${escapeHtml(cust.area || 'No location')}</span>
                    </div>
                    ${cust.usageCount > 1 ? `<span class="autocomplete-tag">${cust.usageCount} bills</span>` : ''}
                </div>
            `,
            onSelect: (cust) => {
                shopNameInput.value = cust.shopName;
                if (cust.area) {
                    areaInput.value = cust.area;
                }
                areaInput.focus();
                showToast(`Selected customer: ${cust.shopName}`, 'info', 2000);
                loadCustomerRecommendations(cust.shopName);
            }
        });
    }

    // 2. Product Autocomplete
    const productDropdown = document.getElementById('productAutocomplete');
    if (productNameInput && productDropdown) {
        setupAutocomplete({
            inputEl: productNameInput,
            dropdownEl: productDropdown,
            fetchUrl: '/api/autocomplete/products?q=',
            dataKey: 'products',
            renderItem: (prod, idx) => {
                const hasPrice = prod.price !== undefined && prod.price !== null && Number(prod.price) > 0;
                const priceFormatted = hasPrice ? `₹${Number(prod.price).toFixed(2)}` : '';
                return `
                    <div class="autocomplete-item" data-index="${idx}">
                        <div class="autocomplete-info">
                            <span class="autocomplete-name">${escapeHtml(prod.name)}</span>
                            <span class="autocomplete-sep">—</span>
                            <span class="autocomplete-detail">${hasPrice ? `Last price: ${priceFormatted}` : 'No previous price'}</span>
                        </div>
                        ${hasPrice ? `<span class="autocomplete-tag autocomplete-price-tag">${priceFormatted}</span>` : ''}
                    </div>
                `;
            },
            onSelect: (prod) => {
                productNameInput.value = prod.name;
                const hasPrice = prod.price !== undefined && prod.price !== null && Number(prod.price) > 0;
                if (hasPrice) {
                    priceInput.value = Number(prod.price).toFixed(2);
                }
                updateLiveTotal();
                // Focus quantity input for fast entry; do NOT automatically add product to invoice table
                quantityInput.focus();
                showToast(`Selected product: ${prod.name}`, 'info', 2000);
            }
        });
    }
}

// Live total calculation
function updateLiveTotal() {
    const quantity = parseFloat(quantityInput.value) || 0;
    const price = parseFloat(priceInput.value) || 0;
    const total = quantity * price;
    
    if (total > 0) {
        // Show live preview next to price field
        let preview = document.getElementById('livePreview');
        if (!preview) {
            preview = document.createElement('div');
            preview.id = 'livePreview';
            preview.className = 'live-preview';
            priceInput.parentElement.appendChild(preview);
        }
        preview.textContent = `Total: ₹${total.toFixed(2)}`;
        preview.style.display = 'block';
    } else {
        const preview = document.getElementById('livePreview');
        if (preview) preview.style.display = 'none';
    }
}

// Toast notification system
function showToast(message, type = 'info', duration = 3000) {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    const icon = {
        success: '✅',
        error: '❌',
        warning: '⚠️',
        info: 'ℹ️'
    }[type] || 'ℹ️';
    
    toast.innerHTML = `
        <span class="toast-icon">${icon}</span>
        <span class="toast-message">${message}</span>
        <button class="toast-close" onclick="this.parentElement.remove()">×</button>
    `;
    
    container.appendChild(toast);
    
    // Trigger animation
    setTimeout(() => toast.classList.add('toast-show'), 10);
    
    // Auto remove
    setTimeout(() => {
        toast.classList.remove('toast-show');
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// Enhanced add product with toast
const originalAddProduct = addProduct;
addProduct = function() {
    const productName = productNameInput.value.trim();
    
    if (productName) {
        originalAddProduct.call(this);
        showToast(`Added: ${productName}`, 'success', 2000);
        
        // Clear live preview
        const preview = document.getElementById('livePreview');
        if (preview) preview.style.display = 'none';
    }
};