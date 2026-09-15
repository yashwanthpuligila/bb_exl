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

async function checkSystemEngineStatus() {
    try {
        const res = await fetch('/api/status');
        const data = await res.json();
        if (data.success) {
            const statusTextEl = document.getElementById('systemStatusText');
            const dbTitleEl = document.getElementById('dbBrowserTitle');
            const dbSubtitleEl = document.getElementById('dbBrowserSubtitle');
            if (data.is_postgres) {
                if (statusTextEl) statusTextEl.textContent = 'PostgreSQL Cloud DB Active';
                if (dbTitleEl) dbTitleEl.textContent = '🗄️ PostgreSQL Database Browser';
                if (dbSubtitleEl) dbSubtitleEl.textContent = 'Render Production Cloud Database (PostgreSQL: bbExcel-postgre)';
            } else {
                if (statusTextEl) statusTextEl.textContent = 'SQLite Local DB Active';
                if (dbTitleEl) dbTitleEl.textContent = '🗄️ SQLite Database Browser';
                if (dbSubtitleEl) dbSubtitleEl.textContent = 'Local Windows Desktop Database (SQLite: invoice_learning.db)';
            }
        }
    } catch (e) {
        console.warn('Status check warning:', e);
    }
}

// Desktop Window Lifecycle Heartbeat (Informational only; does not terminate backend)
function initDesktopLifecycle() {
    if (window.location.protocol === 'file:') return;
    
    const sessionId = 'desktop_' + Math.random().toString(36).substring(2, 10);

    function sendHeartbeat() {
        fetch('/api/desktop/heartbeat?session=' + sessionId, {
            method: 'POST',
            cache: 'no-store'
        }).catch(function() {});
    }

    sendHeartbeat();
    setInterval(sendHeartbeat, 5000);
}

// Event listeners
document.addEventListener('DOMContentLoaded', function() {
    initDesktopLifecycle();
    checkSystemEngineStatus();
    updateAppBadges();
    if (window.location.protocol === 'file:') {
        alert('⚠️ NOTICE: You opened this file directly from your disk (file://).\n\nTo connect to the database and generate invoices, please open:\n• http://localhost:5000\n• or double-click "run_desktop_app.bat"');
    }
    initPwaInstall();
    addProductBtn.addEventListener('click', addProduct);
    clearAllBtn.addEventListener('click', clearAll);
    generateInvoiceBtn.addEventListener('click', generateInvoice);
    
    // Set Header Current Date
    const dateHeaderEl = document.getElementById('currentDateHeader');
    if (dateHeaderEl) {
        const now = new Date();
        dateHeaderEl.textContent = now.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' });
    }
    
    // --- ERP Navigation & View Switching ---
    document.querySelectorAll('.nav-item[data-view]').forEach(item => {
        item.addEventListener('click', function() {
            const targetView = this.dataset.view;
            if (targetView) switchView(targetView);
        });
    });

    const btnTopNewInv = document.getElementById('btnTopNewInvoice');
    if (btnTopNewInv) {
        btnTopNewInv.addEventListener('click', () => {
            resetCreateInvoiceForm();
            switchView('create-invoice');
            if (shopNameInput) shopNameInput.focus();
        });
    }

    const globalDateRangeEl = document.getElementById('globalDateRange');
    if (globalDateRangeEl) {
        globalDateRangeEl.addEventListener('change', function() {
            loadDashboard(this.value);
        });
    }

    // Sidebar Mobile Toggle
    const sidebarToggleBtn = document.getElementById('sidebarToggle');
    const appSidebar = document.getElementById('appSidebar');
    const sidebarOverlay = document.getElementById('sidebarOverlay');
    if (sidebarToggleBtn && appSidebar && sidebarOverlay) {
        sidebarToggleBtn.addEventListener('click', () => {
            appSidebar.classList.toggle('mobile-open');
            sidebarOverlay.classList.toggle('active');
        });
        sidebarOverlay.addEventListener('click', () => {
            appSidebar.classList.remove('mobile-open');
            sidebarOverlay.classList.remove('active');
        });
    }

    // Dashboard Quick Links
    const linkViewInvoices = document.getElementById('linkViewAllInvoices');
    if (linkViewInvoices) {
        linkViewInvoices.addEventListener('click', () => switchView('invoices'));
    }
    const linkViewCustomers = document.getElementById('linkViewAllCustomers');
    if (linkViewCustomers) {
        linkViewCustomers.addEventListener('click', () => switchView('customers'));
    }

    // --- Invoices Directory Filters ---
    const invSearch = document.getElementById('invoiceSearchInput');
    if (invSearch) {
        invSearch.addEventListener('input', debounce(() => loadInvoicesTable(), 300));
    }
    const invClearSearch = document.getElementById('invoiceClearSearchBtn');
    if (invClearSearch) {
        invClearSearch.addEventListener('click', () => {
            if (invSearch) invSearch.value = '';
            loadInvoicesTable();
        });
    }
    const invCustSelect = document.getElementById('invoiceCustomerSelect');
    if (invCustSelect) invCustSelect.addEventListener('change', loadInvoicesTable);
    const invDateSelect = document.getElementById('invoiceDateSelect');
    if (invDateSelect) invDateSelect.addEventListener('change', loadInvoicesTable);
    const invTypeSelect = document.getElementById('invoiceTypeSelect');
    if (invTypeSelect) invTypeSelect.addEventListener('change', loadInvoicesTable);
    const invSortSelect = document.getElementById('invoiceSortSelect');
    if (invSortSelect) invSortSelect.addEventListener('change', loadInvoicesTable);
    const invResetBtn = document.getElementById('btnResetInvoiceFilters');
    if (invResetBtn) {
        invResetBtn.addEventListener('click', () => {
            if (invSearch) invSearch.value = '';
            if (invCustSelect) invCustSelect.value = '';
            if (invDateSelect) invDateSelect.value = 'all';
            if (invTypeSelect) invTypeSelect.value = '';
            if (invSortSelect) invSortSelect.value = 'date_desc';
            loadInvoicesTable();
        });
    }

    // --- Customers Directory Filters ---
    const custSearch = document.getElementById('customerSearchInput');
    if (custSearch) {
        custSearch.addEventListener('input', debounce(() => loadCustomersTable(), 300));
    }
    const custSort = document.getElementById('customerSortSelect');
    if (custSort) custSort.addEventListener('change', loadCustomersTable);

    // --- Products Directory Filters ---
    const prodSearch = document.getElementById('productSearchInput');
    if (prodSearch) {
        prodSearch.addEventListener('input', debounce(() => loadProductsTable(), 300));
    }
    const prodSort = document.getElementById('productSortSelect');
    if (prodSort) prodSort.addEventListener('change', loadProductsTable);

    // --- Customer Modal Drawer Close ---
    const custModalClose = document.getElementById('custModalCloseBtn');
    const custModalOverlay = document.getElementById('customerModalOverlay');
    if (custModalClose) custModalClose.addEventListener('click', closeCustomerModal);
    if (custModalOverlay) custModalOverlay.addEventListener('click', closeCustomerModal);

    // --- Product Modal Drawer Close ---
    const prodModalClose = document.getElementById('prodModalCloseBtn');
    const prodModalOverlay = document.getElementById('productModalOverlay');
    if (prodModalClose) prodModalClose.addEventListener('click', closeProductModal);
    if (prodModalOverlay) prodModalOverlay.addEventListener('click', closeProductModal);

    // --- Reset All Data Modal ---
    initResetModal();

    // --- Delete Modals & Bulk Actions ---
    initDeleteModals();

    // --- Edit Invoice Modal ---
    initEditInvoiceModal();

    // Load initial dashboard
    loadDashboard('30d');
    
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
    ['input', 'change', 'keyup'].forEach(evt => {
        if (quantityInput) quantityInput.addEventListener(evt, updateLiveTotal);
        if (priceInput) priceInput.addEventListener(evt, updateLiveTotal);
        if (productNameInput) productNameInput.addEventListener(evt, function() {
            if (!this.value.trim() && (!quantityInput.value || !priceInput.value)) {
                updateLiveTotal();
            }
        });
    });
    
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

    // Extra Charges input listeners for live total recalculation
    const extraChargesAmountInput = document.getElementById('extraChargesAmount');
    const extraChargesDescInput = document.getElementById('extraChargesDesc');
    if (extraChargesAmountInput) extraChargesAmountInput.addEventListener('input', updateTotal);
    if (extraChargesDescInput) extraChargesDescInput.addEventListener('input', updateTotal);

    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeInvoiceModal();
            closeCustomerModal();
            closeProductModal();
            closeResetModal();
            closeDeleteInvoiceModal();
            closeBulkDeleteModal();
            closeDeleteCustomerModal();
            closeDeleteProductModal();
            closeEditInvoiceModal();
        }
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
    updateLiveTotal();
    productNameInput.focus();
    
    // Update display
    updateProductsList();
    updateTotal();
    
    // Load recommendations after adding product
    loadRecommendations();
    
    showStatus(`Added: ${productName}`, 'success');
    if (typeof showToast === 'function') {
        showToast(`Added: ${productName}`, 'success', 2000);
    }
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

// Update total amount and live breakdown with Extra Charges
function updateTotal() {
    const subtotal = products.reduce((sum, product) => sum + product.total, 0);
    const extraAmtInput = document.getElementById('extraChargesAmount');
    const extraDescInput = document.getElementById('extraChargesDesc');
    const extraAmt = parseFloat(extraAmtInput?.value) || 0;
    const extraDesc = (extraDescInput?.value || '').trim() || 'Extra Charges';
    const grandTotal = subtotal + (extraAmt > 0 ? extraAmt : 0);

    const subtotalEl = document.getElementById('productSubtotalDisplay');
    const extraRowEl = document.getElementById('extraChargesDisplayRow');
    const extraLabelEl = document.getElementById('extraChargesDisplayLabel');
    const extraAmountEl = document.getElementById('extraChargesDisplayAmount');

    if (subtotalEl) subtotalEl.textContent = `₹${formatIndianCurrency(subtotal)}`;
    if (extraRowEl) {
        if (extraAmt > 0) {
            extraRowEl.style.display = 'flex';
            if (extraLabelEl) extraLabelEl.textContent = `${extraDesc}:`;
            if (extraAmountEl) extraAmountEl.textContent = `+₹${formatIndianCurrency(extraAmt)}`;
        } else {
            extraRowEl.style.display = 'none';
        }
    }

    if (totalAmount) totalAmount.textContent = `₹${formatIndianCurrency(grandTotal)}`;
}

// Reset and reload the Create Invoice form
function resetCreateInvoiceForm() {
    // 1. Clear customer inputs
    if (shopNameInput) shopNameInput.value = '';
    if (areaInput) areaInput.value = '';
    
    // 2. Clear product inputs
    if (productNameInput) productNameInput.value = '';
    if (quantityInput) quantityInput.value = '';
    if (priceInput) priceInput.value = '';
    
    // 3. Explicitly hide and clear live preview
    const preview = document.getElementById('livePreview');
    if (preview) {
        preview.textContent = '';
        preview.style.display = 'none';
    }
    
    // 4. Clear products array and extra charges
    products = [];
    const extraDescInput = document.getElementById('extraChargesDesc');
    const extraAmtInput = document.getElementById('extraChargesAmount');
    if (extraDescInput) extraDescInput.value = '';
    if (extraAmtInput) extraAmtInput.value = '0.00';
    
    // 5. Reset invoice type radio to 'current'
    const currentRadio = document.querySelector('input[name="invoiceType"][value="current"]');
    if (currentRadio) currentRadio.checked = true;
    
    // 6. Hide customer recommendations
    const recSection = document.getElementById('recommendationsSection');
    if (recSection) recSection.style.display = 'none';
    
    // 7. Hide autocomplete dropdowns
    const custDropdown = document.getElementById('customerAutocomplete');
    const prodDropdown = document.getElementById('productAutocomplete');
    if (custDropdown) custDropdown.style.display = 'none';
    if (prodDropdown) prodDropdown.style.display = 'none';
    
    // 8. Reset validation and status message
    if (statusMessage) {
        statusMessage.textContent = '';
        statusMessage.className = 'status-message';
    }
    
    // 9. Re-render empty lists and totals
    updateProductsList();
    updateTotal();
    if (typeof updateLiveTotal === 'function') {
        updateLiveTotal();
    }
}

// Clear all function
function clearAll() {
    const hasData = products.length > 0 ||
        (shopNameInput && shopNameInput.value.trim() !== '') ||
        (areaInput && areaInput.value.trim() !== '') ||
        (productNameInput && productNameInput.value.trim() !== '') ||
        (document.getElementById('extraChargesDesc')?.value || '').trim() !== '';
        
    if (!hasData) {
        showStatus('Form is already clear', 'info');
        return;
    }
    
    if (confirm('Are you sure you want to clear the entire invoice form?')) {
        resetCreateInvoiceForm();
        showStatus('Invoice form cleared', 'info');
        if (shopNameInput) shopNameInput.focus();
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
        if (typeof showToast === 'function') showToast('Please enter Shop Name', 'error');
        shopNameInput.focus();
        return;
    }
    
    if (!area) {
        showStatus('Please enter area', 'error');
        if (typeof showToast === 'function') showToast('Please enter Area', 'error');
        areaInput.focus();
        return;
    }

    // Auto-add current product if user typed into product inputs but forgot to click "Add Product"
    const pName = productNameInput.value.trim();
    const pQty = parseInt(quantityInput.value);
    const pPrice = parseFloat(priceInput.value);
    if (pName && pQty > 0 && pPrice >= 0) {
        addProduct();
    }
    
    if (products.length === 0) {
        showStatus('Please add at least one product before generating invoice', 'error');
        if (typeof showToast === 'function') showToast('Please add at least one product', 'error');
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
        
        const extraChargesDesc = (document.getElementById('extraChargesDesc')?.value || '').trim();
        const extraChargesAmount = parseFloat(document.getElementById('extraChargesAmount')?.value) || 0.0;
        if (extraChargesAmount < 0) {
            showToast('Extra charges amount cannot be negative', 'error');
            showStatus('Extra charges amount cannot be negative', 'error');
            showLoading(false);
            return;
        }

        const productSubtotal = products.reduce((sum, p) => sum + p.total, 0);
        const grandTotal = productSubtotal + (extraChargesAmount > 0 ? extraChargesAmount : 0);

        const invoiceData = {
            customer: {
                shopName: shopName,
                area: area
            },
            products: JSON.parse(JSON.stringify(products)),
            invoiceNumber: generateInvoiceNumber(),
            date: formattedDate,
            total: grandTotal,
            productSubtotal: productSubtotal,
            extraChargesDesc: extraChargesDesc,
            extraChargesAmount: extraChargesAmount,
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
            
            // Automatically reset and reload the invoice creation form for the next invoice
            resetCreateInvoiceForm();
            
            showToast('Tax Invoice generated successfully!', 'success', 3000);
            showStatus('Invoice generated successfully! Form reset for next invoice.', 'success');
            
            // Refresh customer recommendations immediately with the updated order history
            loadCustomerRecommendations(shopName);
            if (typeof loadDashboard === 'function') {
                const curRange = document.getElementById('globalDateRange')?.value || 'all';
                loadDashboard(curRange);
            }
            if (typeof updateAppBadges === 'function') {
                updateAppBadges();
            }
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
                      
    const productSubtotal = products.reduce((sum, p) => sum + (Number(p.total) || 0), 0);
    const totalQty = products.reduce((sum, p) => sum + (Number(p.quantity) || 0), 0);
    
    const extraChargesAmt = Number(invoiceData.extraChargesAmount !== undefined ? invoiceData.extraChargesAmount : ((historyData && historyData.extra_charges_amount) || 0));
    const extraChargesDesc = String(invoiceData.extraChargesDesc || (historyData && historyData.extra_charges_desc) || '').trim();
    const hasExtraCharges = extraChargesAmt > 0;
    const currentOrderTotal = productSubtotal + (hasExtraCharges ? extraChargesAmt : 0);

    let prevTotal = 0;
    if (isHistory) {
        prevTotal = historyData.previous_orders.reduce((sum, ord) => sum + (Number(ord.total) || 0), 0);
    }
    
    const finalGrandTotal = isHistory ? (historyData.grand_total || (prevTotal + currentOrderTotal)) : currentOrderTotal;
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
                                <td class="text-right font-semibold">${hasExtraCharges ? 'Product Subtotal:' : 'Current Order Total:'}</td>
                                <td class="text-right font-bold amount-highlight">₹${formatIndianCurrency(productSubtotal)}</td>
                            </tr>
                            ${hasExtraCharges ? `
                            <tr class="tfoot-extra-charges" style="background: #F8FAFC;">
                                <td colspan="3" class="text-left" style="color: #4F46E5; font-weight: 600; font-size: 11px;">
                                    🚚 ${escapeHtml(extraChargesDesc || 'Extra Charges')}
                                </td>
                                <td class="text-right font-semibold" style="color: #4F46E5;">${escapeHtml(extraChargesDesc || 'Extra Charges')}:</td>
                                <td class="text-right font-bold" style="color: #4F46E5;">₹${formatIndianCurrency(extraChargesAmt)}</td>
                            </tr>
                            <tr class="tfoot-order-total" style="background: #EEF2FF;">
                                <td colspan="3"></td>
                                <td class="text-right font-bold" style="color: #1E1B4B;">Current Order Total:</td>
                                <td class="text-right font-bold" style="color: #1E1B4B; font-size: 13px;">₹${formatIndianCurrency(currentOrderTotal)}</td>
                            </tr>
                            ` : ''}
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
                            ${hasExtraCharges ? `
                            <tr>
                                <td class="t-lbl">Product Subtotal:</td>
                                <td class="t-val">₹${formatIndianCurrency(productSubtotal)}</td>
                            </tr>
                            <tr>
                                <td class="t-lbl">${escapeHtml(extraChargesDesc || 'Extra Charges')}:</td>
                                <td class="t-val" style="color: #4F46E5; font-weight: 700;">+₹${formatIndianCurrency(extraChargesAmt)}</td>
                            </tr>
                            ` : ''}
                            <tr>
                                <td class="t-lbl">Current Order Total:</td>
                                <td class="t-val">₹${formatIndianCurrency(currentOrderTotal)}</td>
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
    // Also render inside dedicated print root
    const printRoot = document.getElementById('printInvoiceRoot');
    if (printRoot) {
        printRoot.innerHTML = invoiceHtml;
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
    resetCreateInvoiceForm();
}

// Print invoice reliably using dedicated #printInvoiceRoot and native window.print()
async function printInvoice() {
    const modal = document.getElementById('invoiceModal');
    const printArea = document.getElementById('invoicePrintArea');
    const printRoot = document.getElementById('printInvoiceRoot');
    
    if ((!modal || !modal.classList.contains('active')) && !currentInvoiceData && (!printArea || !printArea.children.length)) {
        showToast('Please generate or select an invoice before printing', 'warning');
        return;
    }

    // Render current invoice data inside #printInvoiceRoot before calling window.print()
    if (printRoot) {
        if (currentInvoiceData) {
            printRoot.innerHTML = renderInvoiceHTML(currentInvoiceData, currentHistoryData);
        } else if (printArea && printArea.children.length > 0) {
            printRoot.innerHTML = printArea.innerHTML;
        }
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

// Ensure #printInvoiceRoot always has the current invoice rendered if triggered via keyboard (Ctrl+P)
window.addEventListener('beforeprint', () => {
    const printRoot = document.getElementById('printInvoiceRoot');
    const printArea = document.getElementById('invoicePrintArea');
    if (printRoot) {
        if (currentInvoiceData) {
            printRoot.innerHTML = renderInvoiceHTML(currentInvoiceData, currentHistoryData);
        } else if (printArea && printArea.children.length > 0) {
            printRoot.innerHTML = printArea.innerHTML;
        }
    }
});

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
    const extraChargesAmt = Number(currentInvoiceData.extraChargesAmount || (currentHistoryData && currentHistoryData.extra_charges_amount) || 0);
    const extraChargesDesc = String(currentInvoiceData.extraChargesDesc || (currentHistoryData && currentHistoryData.extra_charges_desc) || '').trim();
    if (extraChargesAmt > 0) {
        const subtotal = productsList.reduce((s, p) => s + (Number(p.total) || 0), 0);
        text += `*Product Subtotal:* ₹${formatIndianCurrency(subtotal)}\n`;
        text += `*${extraChargesDesc || 'Extra Charges'}:* ₹${formatIndianCurrency(extraChargesAmt)}\n`;
    }
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
    const qtyVal = quantityInput ? quantityInput.value.trim() : '';
    const priceVal = priceInput ? priceInput.value.trim() : '';
    const preview = document.getElementById('livePreview');
    
    if (qtyVal === '' || priceVal === '') {
        if (preview) {
            preview.textContent = '';
            preview.style.display = 'none';
        }
        return;
    }
    
    const quantity = parseFloat(qtyVal);
    const price = parseFloat(priceVal);
    
    if (!isNaN(quantity) && !isNaN(price) && quantity > 0 && price > 0) {
        const total = quantity * price;
        if (!preview) {
            const p = document.createElement('div');
            p.id = 'livePreview';
            p.className = 'live-preview';
            if (priceInput && priceInput.parentElement) {
                priceInput.parentElement.appendChild(p);
            }
            p.textContent = `Total: ₹${total.toFixed(2)}`;
            p.style.display = 'block';
        } else {
            preview.textContent = `Total: ₹${total.toFixed(2)}`;
            preview.style.display = 'block';
        }
    } else {
        if (preview) {
            preview.textContent = '';
            preview.style.display = 'none';
        }
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


/* ==========================================================================
   ERP DASHBOARD CONTROLLER & WORKSPACE LOGIC
   ========================================================================== */

let currentActiveView = 'dashboard';
let salesChartInstance = null;

// Switch between the 5 primary views
function switchView(viewName) {
    currentActiveView = viewName;
    
    // Update active nav button
    document.querySelectorAll('.nav-item[data-view]').forEach(btn => {
        if (btn.dataset.view === viewName) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    // Close mobile sidebar if open
    const sidebar = document.getElementById('appSidebar');
    const overlay = document.getElementById('sidebarOverlay');
    if (sidebar) sidebar.classList.remove('mobile-open');
    if (overlay) overlay.classList.remove('active');

    // Show/hide view containers
    const viewContainers = {
        'dashboard': document.getElementById('viewDashboard'),
        'create-invoice': document.getElementById('viewCreateInvoice'),
        'invoices': document.getElementById('viewInvoices'),
        'customers': document.getElementById('viewCustomers'),
        'products': document.getElementById('viewProducts'),
        'database': document.getElementById('viewDatabase')
    };

    Object.keys(viewContainers).forEach(v => {
        if (viewContainers[v]) {
            if (v === viewName) {
                viewContainers[v].style.display = 'block';
                viewContainers[v].classList.add('active');
            } else {
                viewContainers[v].style.display = 'none';
                viewContainers[v].classList.remove('active');
            }
        }
    });

    // Update Topbar Title & Subtitle & Date range visibility
    const titleEl = document.getElementById('pageTitle');
    const subtitleEl = document.getElementById('pageSubtitle');
    const topDateContainer = document.getElementById('topDateRangeContainer');

    const meta = {
        'dashboard': {
            title: 'Dashboard',
            subtitle: 'Real-time revenue, invoices, and business analytics',
            showDate: true
        },
        'create-invoice': {
            title: 'Create Invoice',
            subtitle: 'Generate professional A4 Tax Invoice with learning autocomplete',
            showDate: false
        },
        'invoices': {
            title: 'Invoices',
            subtitle: 'Searchable, filterable directory of all saved customer invoices',
            showDate: false
        },
        'customers': {
            title: 'Customers',
            subtitle: 'Customer directory, purchase frequency, and total spend',
            showDate: false
        },
        'products': {
            title: 'Products',
            subtitle: 'Product catalog, pricing intelligence, and sales performance',
            showDate: false
        },
        'database': {
            title: 'Database Browser',
            subtitle: 'Live inspection of SQLite database tables, rows, and schema',
            showDate: false
        }
    }[viewName] || { title: 'Dashboard', subtitle: '', showDate: true };

    if (titleEl) titleEl.textContent = meta.title;
    if (subtitleEl) subtitleEl.textContent = meta.subtitle;
    if (topDateContainer) {
        topDateContainer.style.display = meta.showDate ? 'flex' : 'none';
    }

    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });

    // Load data for view
    if (viewName === 'dashboard') {
        const dateRange = document.getElementById('globalDateRange')?.value || 'all';
        loadDashboard(dateRange);
    } else if (viewName === 'invoices') {
        loadInvoicesTable();
    } else if (viewName === 'customers') {
        loadCustomersTable();
    } else if (viewName === 'products') {
        loadProductsTable();
    } else if (viewName === 'create-invoice') {
        if (typeof updateLiveTotal === 'function') {
            updateLiveTotal();
        }
    } else if (viewName === 'database') {
        loadDatabaseBrowser();
    }
}

// Dashboard Controller
async function loadDashboard(dateRange = 'all') {
    try {
        const res = await fetch(`/api/dashboard?range=${encodeURIComponent(dateRange)}`);
        const data = await res.json();
        if (!data.success) {
            console.error('Failed to load dashboard:', data.error);
            return;
        }

        const m = data.metrics || {};
        
        // Update metric values
        const elSales = document.getElementById('dashTotalSales');
        const elMonth = document.getElementById('dashThisMonthSales');
        const elInvoices = document.getElementById('dashTotalInvoices');
        const elCustomers = document.getElementById('dashTotalCustomers');
        const elProducts = document.getElementById('dashTotalProducts');
        const elAov = document.getElementById('dashAvgOrderValue');

        if (elSales) elSales.textContent = formatIndianCurrency(m.totalSales || 0);
        if (elMonth) elMonth.textContent = formatIndianCurrency(m.thisMonthSales || 0);
        if (elInvoices) elInvoices.textContent = (m.totalInvoices || 0).toLocaleString('en-IN');
        if (elCustomers) elCustomers.textContent = (m.totalCustomers || 0).toLocaleString('en-IN');
        if (elProducts) elProducts.textContent = (m.totalProducts || 0).toLocaleString('en-IN');
        if (elAov) elAov.textContent = formatIndianCurrency(m.averageOrderValue || 0);

        // Update sidebar badges (always maintain total/all-time counts)
        const badgeInv = document.getElementById('badgeInvoiceCount');
        const badgeCust = document.getElementById('badgeCustomerCount');
        const badgeProd = document.getElementById('badgeProductCount');
        if (badgeInv) badgeInv.textContent = m.allTimeInvoices !== undefined ? m.allTimeInvoices : (m.totalInvoices || 0);
        if (badgeCust) badgeCust.textContent = m.totalCustomers || 0;
        if (badgeProd) badgeProd.textContent = m.totalProducts || 0;

        // Update period label
        const periodLabels = {
            '7d': 'Last 7 Days',
            '30d': 'Last 30 Days',
            'this_year': 'This Year',
            'all': 'All Time'
        };
        const periodLabelEl = document.getElementById('chartPeriodLabel');
        if (periodLabelEl) periodLabelEl.textContent = periodLabels[dateRange] || 'Last 30 Days';

        // Render Sales Chart
        renderSalesChart(data.chart || { labels: [], sales: [], orders: [] });

        // Render Recent Invoices
        renderRecentInvoices(data.recentInvoices || []);

        // Load Top Customers in parallel
        loadTopCustomers();

    } catch (err) {
        console.error('Error in loadDashboard:', err);
    }
}

// Render Sales Revenue Trend Chart using Chart.js
function renderSalesChart(chartData) {
    const canvas = document.getElementById('salesChart');
    if (!canvas) return;

    if (typeof Chart === 'undefined') {
        console.warn('Chart.js not loaded yet');
        return;
    }

    const ctx = canvas.getContext('2d');
    if (salesChartInstance) {
        salesChartInstance.destroy();
    }

    const gradient = ctx.createLinearGradient(0, 0, 0, 260);
    gradient.addColorStop(0, 'rgba(79, 70, 229, 0.35)');
    gradient.addColorStop(1, 'rgba(79, 70, 229, 0.01)');

    const labels = chartData.labels && chartData.labels.length ? chartData.labels : ['No Data'];
    const sales = chartData.sales && chartData.sales.length ? chartData.sales : [0];

    salesChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Sales Revenue (₹)',
                data: sales,
                borderColor: '#4F46E5',
                borderWidth: 2.5,
                backgroundColor: gradient,
                fill: true,
                tension: 0.35,
                pointBackgroundColor: '#FFFFFF',
                pointBorderColor: '#4F46E5',
                pointBorderWidth: 2,
                pointRadius: 4,
                pointHoverRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#0F172A',
                    titleColor: '#F8FAFC',
                    bodyColor: '#F8FAFC',
                    padding: 10,
                    cornerRadius: 8,
                    callbacks: {
                        label: function(context) {
                            return ' Sales: ₹' + formatIndianCurrency(context.parsed.y);
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { display: false, drawBorder: false },
                    ticks: { color: '#64748B', font: { size: 11 } }
                },
                y: {
                    grid: { color: '#F1F5F9', drawBorder: false },
                    ticks: {
                        color: '#64748B',
                        font: { size: 11 },
                        callback: function(val) {
                            if (val >= 100000) return '₹' + (val / 100000).toFixed(1) + 'L';
                            if (val >= 1000) return '₹' + (val / 1000).toFixed(0) + 'k';
                            return '₹' + val;
                        }
                    }
                }
            }
        }
    });
}

// Render Recent Invoices on Dashboard
function renderRecentInvoices(invoices) {
    const tbody = document.getElementById('dashRecentInvoicesBody');
    if (!tbody) return;

    if (!invoices || !invoices.length) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="loading-state">No recent invoices found.</td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = invoices.map(inv => {
        const typeBadgeClass = inv.invoiceType === 'all' ? 'badge-all' : 'badge-current';
        const typeBadgeText = inv.invoiceType === 'all' ? 'All Bills' : 'Current';
        return `
            <tr data-invoice-number="${escapeHtml(inv.invoiceNumber)}" id="dash-invoice-row-${escapeHtml(inv.invoiceNumber)}">
                <td>
                    <strong class="text-primary-color" style="cursor:pointer;" onclick="previewInvoiceByNumber('${escapeHtml(inv.invoiceNumber)}')">
                        ${escapeHtml(inv.invoiceNumber)}
                    </strong>
                </td>
                <td>
                    <strong style="color:#0F172A; cursor:pointer;" onclick="openCustomerModal('${escapeHtml(inv.customerName)}')">${escapeHtml(inv.customerName)}</strong>
                </td>
                <td>
                    <span class="cust-area-pill">${escapeHtml(inv.area || 'Wholesale')}</span>
                </td>
                <td>
                    <div>${escapeHtml(inv.dateFormatted || inv.date)}</div>
                    <span class="relative-time">${escapeHtml(inv.relativeDate || '')}</span>
                </td>
                <td>
                    <span class="badge-type ${typeBadgeClass}">${typeBadgeText}</span>
                </td>
                <td class="text-right font-bold" style="color:#0F172A;">
                    ₹${formatIndianCurrency(inv.totalAmount)}
                </td>
                <td class="text-center">
                    <div class="action-btn-group">
                        <button type="button" class="btn-action" title="Preview Tax Invoice" onclick="previewInvoiceByNumber('${escapeHtml(inv.invoiceNumber)}')">
                            👁️
                        </button>
                        <button type="button" class="btn-action action-edit" title="Edit Invoice" data-action="edit-invoice" data-invoice-number="${escapeHtml(inv.invoiceNumber)}" onclick="openEditInvoiceModal('${escapeHtml(inv.invoiceNumber)}')">
                            ✏️
                        </button>
                        <button type="button" class="btn-action" title="Print Invoice" onclick="previewInvoiceByNumber('${escapeHtml(inv.invoiceNumber)}', true)">
                            🖨️
                        </button>
                        ${inv.downloadUrl ? `
                            <a href="${inv.downloadUrl}" class="btn-action action-excel" title="Download Excel" download>
                                📥
                            </a>
                        ` : ''}
                        <button type="button" class="btn-action action-delete" title="Delete Invoice" data-action="delete-invoice" data-id="${escapeHtml(inv.invoiceNumber)}" data-invoice-id="${escapeHtml(inv.invoiceNumber)}" data-invoice-number="${escapeHtml(inv.invoiceNumber)}" data-customer="${escapeHtml(inv.customerName)}" data-date="${escapeHtml(inv.dateFormatted || inv.date)}" data-amount="${inv.totalAmount}" onclick="openDeleteInvoiceModal('${escapeHtml(inv.invoiceNumber)}', '${escapeHtml(inv.customerName)}', '${escapeHtml(inv.dateFormatted || inv.date)}', ${inv.totalAmount})">
                            🗑️
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

// Load Top Customers in Dashboard
async function loadTopCustomers() {
    const container = document.getElementById('dashTopCustomersList');
    if (!container) return;

    try {
        const res = await fetch('/api/customers?sort_by=amount');
        const data = await res.json();
        if (data.success && data.customers && data.customers.length) {
            const top5 = data.customers.slice(0, 5);
            container.innerHTML = top5.map((c, idx) => {
                const rankClass = idx === 0 ? 'rank-1' : idx === 1 ? 'rank-2' : idx === 2 ? 'rank-3' : '';
                return `
                    <div class="top-cust-item" onclick="openCustomerModal('${escapeHtml(c.customerName)}')">
                        <div class="top-cust-left">
                            <span class="top-cust-rank ${rankClass}">${idx + 1}</span>
                            <div>
                                <div class="top-cust-name">${escapeHtml(c.customerName)}</div>
                                <div class="top-cust-area">${escapeHtml(c.area || 'Wholesale')}</div>
                            </div>
                        </div>
                        <div class="top-cust-right">
                            <div class="top-cust-amount">₹${formatIndianCurrency(c.totalAmount)}</div>
                            <div class="top-cust-invoices">${c.invoiceCount} order${c.invoiceCount !== 1 ? 's' : ''}</div>
                        </div>
                    </div>
                `;
            }).join('');
        } else {
            container.innerHTML = '<div class="loading-state">No customer history yet.</div>';
        }
    } catch (e) {
        console.error('Error loading top customers:', e);
    }
}

// Invoices Directory Controller
async function loadInvoicesTable() {
    const tbody = document.getElementById('invoicesTableBody');
    if (tbody) {
        tbody.innerHTML = '<tr><td colspan="8" class="loading-state">Loading invoices...</td></tr>';
    }

    const q = document.getElementById('invoiceSearchInput')?.value || '';
    const customer = document.getElementById('invoiceCustomerSelect')?.value || '';
    const dateRange = document.getElementById('invoiceDateSelect')?.value || 'all';
    const typeFilter = document.getElementById('invoiceTypeSelect')?.value || '';
    const sortVal = document.getElementById('invoiceSortSelect')?.value || 'date_desc';

    let sortBy = 'date';
    let sortOrder = 'desc';
    if (sortVal === 'date_asc') { sortBy = 'date'; sortOrder = 'asc'; }
    else if (sortVal === 'amount_desc') { sortBy = 'amount'; sortOrder = 'desc'; }
    else if (sortVal === 'amount_asc') { sortBy = 'amount'; sortOrder = 'asc'; }
    else if (sortVal === 'customer_asc') { sortBy = 'customer'; sortOrder = 'asc'; }

    const clearBtn = document.getElementById('invoiceClearSearchBtn');
    if (clearBtn) clearBtn.style.display = q ? 'block' : 'none';

    try {
        const url = `/api/invoices?q=${encodeURIComponent(q)}&customer=${encodeURIComponent(customer)}&range=${encodeURIComponent(dateRange)}&type=${encodeURIComponent(typeFilter)}&sort_by=${sortBy}&sort_order=${sortOrder}&limit=150`;
        console.log(`[REQUEST] GET ${url}`);
        const res = await fetch(url);
        console.log(`[RESPONSE] GET ${url} -> ${res.status} ${res.statusText}`);
        const data = await res.json();
        console.log(`[BODY] /api/invoices: totalCount=${data.totalCount}, success=${data.success}`);

        if (!data.success) {
            if (tbody) tbody.innerHTML = `<tr><td colspan="8" class="loading-state" style="color:#ef4444;">${escapeHtml(data.error || 'Failed to load invoices')}</td></tr>`;
            return;
        }

        // Populate customer options if empty
        const custSelect = document.getElementById('invoiceCustomerSelect');
        if (custSelect && custSelect.options.length <= 1 && data.customerOptions) {
            data.customerOptions.forEach(cName => {
                const opt = document.createElement('option');
                opt.value = cName;
                opt.textContent = cName;
                custSelect.appendChild(opt);
            });
        }

        // Summary bar
        const countEl = document.getElementById('invTableCount');
        const totalEl = document.getElementById('invTableTotal');
        if (countEl) countEl.textContent = data.totalCount || 0;
        if (totalEl) totalEl.textContent = '₹' + formatIndianCurrency(data.totalAmount || 0);

        // Keep sidebar badge synchronized with all-time total invoices
        const badgeInv = document.getElementById('badgeInvoiceCount');
        if (badgeInv) {
            badgeInv.textContent = data.allTimeCount !== undefined ? data.allTimeCount : (data.totalCount || 0);
        }

        const invoices = data.invoices || [];
        const selectAll = document.getElementById('selectAllInvoices');
        if (selectAll) selectAll.checked = false;
        updateInvoicesBulkBar();

        if (!invoices.length) {
            if (tbody) tbody.innerHTML = '<tr><td colspan="9" class="loading-state">No matching invoices found.</td></tr>';
            return;
        }

        if (tbody) {
            tbody.innerHTML = invoices.map(inv => {
                const typeBadgeClass = inv.invoiceType === 'all' ? 'badge-all' : 'badge-current';
                const typeBadgeText = inv.invoiceType === 'all' ? 'All Bills' : 'Current';
                const dateStr = inv.dateFormatted || inv.date || '';
                return `
                    <tr data-invoice-number="${escapeHtml(inv.invoiceNumber)}" id="invoice-row-${escapeHtml(inv.invoiceNumber)}">
                        <td style="text-align: center;">
                            <input type="checkbox" class="invoice-row-checkbox invoice-checkbox" value="${escapeHtml(inv.invoiceNumber)}" data-id="${escapeHtml(inv.invoiceNumber)}" data-invoice-id="${escapeHtml(inv.invoiceNumber)}" data-amount="${inv.totalAmount}" onchange="updateInvoicesBulkBar()">
                        </td>
                        <td>
                            <strong class="text-primary-color" style="cursor:pointer;" onclick="previewInvoiceByNumber('${escapeHtml(inv.invoiceNumber)}')">
                                ${escapeHtml(inv.invoiceNumber)}
                            </strong>
                        </td>
                        <td>
                            <strong style="color:#0F172A; cursor:pointer;" onclick="openCustomerModal('${escapeHtml(inv.customerName)}')">
                                ${escapeHtml(inv.customerName)}
                            </strong>
                        </td>
                        <td>
                            <span class="cust-area-pill">${escapeHtml(inv.area || 'Wholesale')}</span>
                        </td>
                        <td>
                            <div>${escapeHtml(dateStr)}</div>
                            <span class="relative-time">${escapeHtml(inv.relativeDate || '')}</span>
                        </td>
                        <td>
                            <span class="badge-type ${typeBadgeClass}">${typeBadgeText}</span>
                        </td>
                        <td class="text-center">
                            <span class="badge-type">${inv.productCount || 0} items</span>
                        </td>
                        <td class="text-right font-bold" style="color:#0F172A;">
                            ₹${formatIndianCurrency(inv.totalAmount)}
                        </td>
                        <td class="text-center">
                            <div class="action-btn-group">
                                <button type="button" class="btn-action" title="Preview Tax Invoice" onclick="previewInvoiceByNumber('${escapeHtml(inv.invoiceNumber)}')">
                                    👁️ Preview
                                </button>
                                <button type="button" class="btn-action action-edit" title="Edit Invoice" data-action="edit-invoice" data-invoice-number="${escapeHtml(inv.invoiceNumber)}" onclick="openEditInvoiceModal('${escapeHtml(inv.invoiceNumber)}')">
                                    ✏️ Edit
                                </button>
                                <button type="button" class="btn-action" title="Print Invoice" onclick="previewInvoiceByNumber('${escapeHtml(inv.invoiceNumber)}', true)">
                                    🖨️ Print
                                </button>
                                ${inv.downloadUrl ? `
                                    <a href="${inv.downloadUrl}" class="btn-action action-excel" title="Download Excel" download>
                                        📥 Excel
                                    </a>
                                ` : ''}
                                <button type="button" class="btn-action action-delete" title="Delete Invoice" data-action="delete-invoice" data-id="${escapeHtml(inv.invoiceNumber)}" data-invoice-id="${escapeHtml(inv.invoiceNumber)}" data-invoice-number="${escapeHtml(inv.invoiceNumber)}" data-customer="${escapeHtml(inv.customerName)}" data-date="${escapeHtml(dateStr)}" data-amount="${inv.totalAmount}" onclick="openDeleteInvoiceModal('${escapeHtml(inv.invoiceNumber)}', '${escapeHtml(inv.customerName)}', '${escapeHtml(dateStr)}', ${inv.totalAmount})">
                                    🗑️
                                </button>
                            </div>
                        </td>
                    </tr>
                `;
            }).join('');
            
            // Attach event delegation if not already attached
            setupInvoicesTableDelegation();
        }

    } catch (err) {
        console.error('[API ERROR] GET /api/invoices:', err);
        if (tbody) tbody.innerHTML = `<tr><td colspan="9" class="loading-state" style="color:#ef4444;">Error loading invoices: ${escapeHtml(err.message)}</td></tr>`;
    }
}

// Customers Directory Controller
async function loadCustomersTable() {
    const grid = document.getElementById('customersCardGrid');
    if (grid) {
        grid.innerHTML = '<div class="loading-state">Loading customer accounts...</div>';
    }

    const q = document.getElementById('customerSearchInput')?.value || '';
    const sortBy = document.getElementById('customerSortSelect')?.value || 'amount';

    try {
        const url = `/api/customers?q=${encodeURIComponent(q)}&sort_by=${encodeURIComponent(sortBy)}`;
        console.log(`[REQUEST] GET ${url}`);
        const res = await fetch(url);
        console.log(`[RESPONSE] GET ${url} -> ${res.status} ${res.statusText}`);
        const data = await res.json();
        console.log(`[BODY] /api/customers: totalCount=${data.totalCount}, success=${data.success}`);

        if (!data.success) {
            if (grid) grid.innerHTML = `<div class="loading-state" style="color:#ef4444;">Failed to load customers: ${escapeHtml(data.error || 'Server error')}</div>`;
            return;
        }

        const countEl = document.getElementById('customersTotalCount');
        if (countEl) countEl.textContent = data.totalCount || 0;

        const customers = data.customers || [];
        if (!customers.length) {
            if (grid) grid.innerHTML = '<div class="loading-state">No matching customers found.</div>';
            return;
        }

        if (grid) {
            grid.innerHTML = customers.map(c => {
                const topProdsHtml = (c.topProducts || []).map(tp => 
                    `<span class="cust-prod-tag">${escapeHtml(tp.name)} (${tp.orders}x)</span>`
                ).join('');

                return `
                    <div class="customer-card">
                        <div>
                            <div class="customer-card-header">
                                <div class="cust-name-box">
                                    <h3>${escapeHtml(c.customerName)}</h3>
                                    <span class="cust-area-pill">📍 ${escapeHtml(c.area || 'Wholesale')}</span>
                                </div>
                            </div>

                            <div class="cust-stat-row">
                                <div class="cust-stat-col">
                                    <span class="cust-stat-lbl">TOTAL SPEND</span>
                                    <span class="cust-stat-val">₹${formatIndianCurrency(c.totalAmount)}</span>
                                </div>
                                <div class="cust-stat-col">
                                    <span class="cust-stat-lbl">INVOICES</span>
                                    <span class="cust-stat-val">${c.invoiceCount}</span>
                                </div>
                                <div class="cust-stat-col">
                                    <span class="cust-stat-lbl">LAST ORDER</span>
                                    <span class="cust-stat-val" style="font-size:0.78rem;">${escapeHtml(c.lastDateFormatted || '-')}</span>
                                </div>
                            </div>

                            ${topProdsHtml ? `
                                <div class="cust-top-prods-title">TOP PURCHASED ITEMS:</div>
                                <div class="cust-top-prods-list">${topProdsHtml}</div>
                            ` : ''}
                        </div>

                        <div class="customer-card-actions">
                            <button type="button" class="btn btn-secondary-sm" onclick="openCustomerModal('${escapeHtml(c.customerName)}')">
                                📑 History & Insights
                            </button>
                            <button type="button" class="btn btn-primary-sm" onclick="createInvoiceForCustomer('${escapeHtml(c.customerName)}', '${escapeHtml(c.area || '')}')">
                                ➕ New Invoice
                            </button>
                            <button type="button" class="btn btn-danger-sm action-delete" onclick="openDeleteCustomerModal('${escapeHtml(c.customerName)}')" title="Delete Customer">
                                🗑️
                            </button>
                        </div>
                    </div>
                `;
            }).join('');
        }

    } catch (e) {
        console.error('Error loading customers:', e);
    }
}

// Products Directory Controller
async function loadProductsTable() {
    const tbody = document.getElementById('productsTableBody');
    if (tbody) {
        tbody.innerHTML = '<tr><td colspan="8" class="loading-state">Loading products...</td></tr>';
    }

    const q = document.getElementById('productSearchInput')?.value || '';
    const sortBy = document.getElementById('productSortSelect')?.value || 'quantity';

    try {
        const url = `/api/products?q=${encodeURIComponent(q)}&sort_by=${encodeURIComponent(sortBy)}`;
        console.log(`[REQUEST] GET ${url}`);
        const res = await fetch(url);
        console.log(`[RESPONSE] GET ${url} -> ${res.status} ${res.statusText}`);
        const data = await res.json();
        console.log(`[BODY] /api/products: totalCount=${data.totalCount}, success=${data.success}`);

        if (!data.success) {
            if (tbody) tbody.innerHTML = `<tr><td colspan="8" class="loading-state" style="color:#ef4444;">${escapeHtml(data.error || 'Failed to load products')}</td></tr>`;
            return;
        }

        const countEl = document.getElementById('productsTotalCount');
        if (countEl) countEl.textContent = data.totalCount || 0;

        const products = data.products || [];
        if (!products.length) {
            if (tbody) tbody.innerHTML = '<tr><td colspan="8" class="loading-state">No matching products found.</td></tr>';
            return;
        }

        if (tbody) {
            tbody.innerHTML = products.map(p => `
                <tr>
                    <td>
                        <strong style="color:#0F172A; cursor:pointer;" onclick="openProductModal('${escapeHtml(p.productName)}')">
                            🏷️ ${escapeHtml(p.productName)}
                        </strong>
                    </td>
                    <td class="text-right font-bold" style="color:#16A34A;">
                        ₹${formatIndianCurrency(p.lastPrice)}
                    </td>
                    <td class="text-right" style="color:#475569;">
                        ₹${formatIndianCurrency(p.avgPrice)}
                    </td>
                    <td class="text-center font-bold">
                        ${p.totalQuantitySold}
                    </td>
                    <td class="text-right font-bold" style="color:#0F172A;">
                        ₹${formatIndianCurrency(p.totalSales)}
                    </td>
                    <td class="text-center">
                        <span class="badge-type">${p.invoiceCount}</span>
                    </td>
                    <td class="text-center">
                        <span class="badge-type" style="background:#EEF2FF; color:#4F46E5;">${p.customerCount}</span>
                    </td>
                    <td class="text-center">
                        <div class="action-btn-group">
                            <button type="button" class="btn-action" onclick="openProductModal('${escapeHtml(p.productName)}')">
                                📊 Details
                            </button>
                            <button type="button" class="btn-action action-delete" onclick="openDeleteProductModal('${escapeHtml(p.productName)}')" title="Delete Product">
                                🗑️
                            </button>
                        </div>
                    </td>
                </tr>
            `).join('');
        }

    } catch (e) {
        console.error('[API ERROR] GET /api/products:', e);
        if (tbody) tbody.innerHTML = `<tr><td colspan="8" class="loading-state" style="color:#ef4444;">Error loading products: ${escapeHtml(e.message)}</td></tr>`;
    }
}

// Customer Detail Modal
async function openCustomerModal(customerName) {
    const modal = document.getElementById('customerModal');
    if (!modal) return;

    showLoading(true);
    try {
        const res = await fetch(`/api/customers/${encodeURIComponent(customerName)}`);
        const data = await res.json();
        if (!data.success || !data.customer) {
            showToast('Customer details not found', 'error');
            return;
        }

        const c = data.customer;
        document.getElementById('custModalName').textContent = c.customerName;
        document.getElementById('custModalArea').textContent = `📍 ${c.area || 'Wholesale'}`;
        document.getElementById('custModalSpend').textContent = '₹' + formatIndianCurrency(c.totalSpend);
        document.getElementById('custModalInvCount').textContent = c.invoiceCount;
        document.getElementById('custModalAOV').textContent = '₹' + formatIndianCurrency(c.averageOrderValue);
        document.getElementById('custModalLastDate').textContent = c.lastDateFormatted || '-';

        // Connect Create Invoice button in drawer
        const createBtn = document.getElementById('custModalCreateInvBtn');
        if (createBtn) {
            createBtn.onclick = () => {
                closeCustomerModal();
                createInvoiceForCustomer(c.customerName, c.area);
            };
        }

        // Connect Delete Customer button in drawer
        const deleteCustBtn = document.getElementById('custModalDeleteBtn');
        if (deleteCustBtn) {
            deleteCustBtn.onclick = () => {
                closeCustomerModal();
                openDeleteCustomerModal(c.customerName);
            };
        }

        // Render frequently ordered products pills
        const recTags = document.getElementById('custModalTopProducts');
        if (recTags) {
            const freqs = c.frequentlyOrdered || [];
            if (freqs.length) {
                recTags.innerHTML = freqs.map(p => `
                    <button type="button" class="rec-pill-interactive" title="Click to add to invoice" onclick="addRecommendedProductDirect('${escapeHtml(p.name)}', ${p.last_price || 0})">
                        <span>🏷️ ${escapeHtml(p.name)}</span>
                        <span style="font-weight:700; color:#4F46E5;">₹${formatIndianCurrency(p.last_price)}</span>
                        <span style="color:#64748B; font-size:0.7rem;">(${p.order_count}x)</span>
                    </button>
                `).join('');
            } else {
                recTags.innerHTML = '<span style="color:#64748B; font-size:0.8rem;">No previous item orders recorded.</span>';
            }
        }

        // Render customer invoices
        const tbody = document.getElementById('custModalInvoicesBody');
        if (tbody) {
            const invs = c.invoices || [];
            if (invs.length) {
                tbody.innerHTML = invs.map(inv => `
                    <tr>
                        <td>
                            <strong class="text-primary-color" style="cursor:pointer;" onclick="previewInvoiceByNumber('${escapeHtml(inv.invoiceNumber)}')">
                                ${escapeHtml(inv.invoiceNumber)}
                            </strong>
                        </td>
                        <td>${escapeHtml(inv.dateFormatted || inv.date)}</td>
                        <td>${inv.productCount || 0} items</td>
                        <td class="text-right font-bold">₹${formatIndianCurrency(inv.totalAmount)}</td>
                        <td class="text-center">
                            <div class="action-btn-group">
                                <button type="button" class="btn-action" title="Preview" onclick="previewInvoiceByNumber('${escapeHtml(inv.invoiceNumber)}')">
                                    👁️
                                </button>
                                <button type="button" class="btn-action" title="Print" onclick="previewInvoiceByNumber('${escapeHtml(inv.invoiceNumber)}', true)">
                                    🖨️
                                </button>
                                ${inv.downloadUrl ? `
                                    <a href="${inv.downloadUrl}" class="btn-action action-excel" title="Download Excel" download>
                                        📥
                                    </a>
                                ` : ''}
                            </div>
                        </td>
                    </tr>
                `).join('');
            } else {
                tbody.innerHTML = '<tr><td colspan="5" class="loading-state">No invoices recorded for this customer.</td></tr>';
            }
        }

        modal.classList.add('active');
        document.body.style.overflow = 'hidden';

    } catch (e) {
        console.error('Error opening customer modal:', e);
    } finally {
        showLoading(false);
    }
}

function closeCustomerModal() {
    const modal = document.getElementById('customerModal');
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = '';
    }
}

// Product Detail Modal
async function openProductModal(productName) {
    const modal = document.getElementById('productModal');
    if (!modal) return;

    showLoading(true);
    try {
        const res = await fetch(`/api/products/${encodeURIComponent(productName)}`);
        const data = await res.json();
        if (!data.success || !data.product) {
            showToast('Product details not found', 'error');
            return;
        }

        const p = data.product;
        document.getElementById('prodModalName').textContent = p.productName;
        document.getElementById('prodModalPrice').textContent = `Current / Last Price: ₹${formatIndianCurrency(p.latestPrice)}`;
        document.getElementById('prodModalRevenue').textContent = '₹' + formatIndianCurrency(p.totalRevenue);
        document.getElementById('prodModalQty').textContent = p.totalQuantitySold;
        document.getElementById('prodModalBuyers').textContent = p.customerCount;
        document.getElementById('prodModalInvoices').textContent = p.invoiceCount;
        
        // Connect Delete Product button in drawer
        const deleteProdBtn = document.getElementById('prodModalDeleteBtn');
        if (deleteProdBtn) {
            deleteProdBtn.onclick = () => {
                closeProductModal();
                openDeleteProductModal(p.productName);
            };
        }

        // Render Buyers
        const buyersBody = document.getElementById('prodModalBuyersBody');
        if (buyersBody) {
            const buyers = p.customers || [];
            if (buyers.length) {
                buyersBody.innerHTML = buyers.map(b => `
                    <tr>
                        <td>
                            <strong style="color:#0F172A; cursor:pointer;" onclick="closeProductModal(); openCustomerModal('${escapeHtml(b.customerName)}')">
                                ${escapeHtml(b.customerName)}
                            </strong>
                        </td>
                        <td class="text-center font-bold">${b.orderCount}</td>
                        <td class="text-center">${b.totalQuantity}</td>
                        <td class="text-right font-bold" style="color:#16A34A;">₹${formatIndianCurrency(b.lastPrice)}</td>
                        <td>${escapeHtml(b.lastOrderedDate || '-')}</td>
                    </tr>
                `).join('');
            } else {
                buyersBody.innerHTML = '<tr><td colspan="5" class="loading-state">No buyers recorded yet.</td></tr>';
            }
        }

        // Render Recent Invoices
        const invBody = document.getElementById('prodModalInvoicesBody');
        if (invBody) {
            const invs = p.recentInvoices || [];
            if (invs.length) {
                invBody.innerHTML = invs.map(inv => `
                    <tr>
                        <td>
                            <strong class="text-primary-color" style="cursor:pointer;" onclick="previewInvoiceByNumber('${escapeHtml(inv.invoiceNumber)}')">
                                ${escapeHtml(inv.invoiceNumber)}
                            </strong>
                        </td>
                        <td>${escapeHtml(inv.customerName)}</td>
                        <td class="text-center">${inv.quantity}</td>
                        <td class="text-right">₹${formatIndianCurrency(inv.price)}</td>
                        <td class="text-right font-bold">₹${formatIndianCurrency(inv.total)}</td>
                        <td>${escapeHtml(inv.dateFormatted)}</td>
                        <td class="text-center">
                            <button type="button" class="btn-action" onclick="previewInvoiceByNumber('${escapeHtml(inv.invoiceNumber)}')">
                                👁️
                            </button>
                        </td>
                    </tr>
                `).join('');
            } else {
                invBody.innerHTML = '<tr><td colspan="7" class="loading-state">No recent invoices for this product.</td></tr>';
            }
        }

        modal.classList.add('active');
        document.body.style.overflow = 'hidden';

    } catch (e) {
        console.error('Error opening product modal:', e);
    } finally {
        showLoading(false);
    }
}

function closeProductModal() {
    const modal = document.getElementById('productModal');
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = '';
    }
}

// Prefill customer and switch to invoice view
function createInvoiceForCustomer(customerName, area) {
    closeCustomerModal();
    closeProductModal();
    switchView('create-invoice');

    if (shopNameInput) shopNameInput.value = customerName;
    if (areaInput) areaInput.value = area || '';

    loadCustomerRecommendations(customerName);
    if (productNameInput) productNameInput.focus();

    showToast(`Loaded customer: ${customerName}`, 'info', 2500);
}

// Add recommended product directly into invoice form
function addRecommendedProductDirect(name, price) {
    closeCustomerModal();
    switchView('create-invoice');

    if (productNameInput) productNameInput.value = name;
    if (priceInput) priceInput.value = price > 0 ? price : '';
    if (quantityInput) {
        quantityInput.value = 1;
        quantityInput.focus();
    }
    updateLiveTotal();
    showToast(`Selected: ${name}`, 'info', 1800);
}

// Universal Invoice Preview & Print for any saved invoice
async function previewInvoiceByNumber(invoiceNumber, autoPrint = false) {
    showLoading(true);
    try {
        const res = await fetch(`/api/invoices/${encodeURIComponent(invoiceNumber)}`);
        const data = await res.json();
        if (!data.success || !data.invoice) {
            showToast('Invoice details not found', 'error');
            return;
        }

        const inv = data.invoice;
        const extraChargesAmount = Number(inv.extraChargesAmount || 0);
        const extraChargesDesc = String(inv.extraChargesDesc || '').trim();
        const productSubtotal = inv.productSubtotal !== undefined ? Number(inv.productSubtotal) : (inv.totalAmount - extraChargesAmount);
        const invoiceData = {
            customer: {
                shopName: inv.customerName,
                area: inv.area
            },
            products: inv.products || [],
            invoiceNumber: inv.invoiceNumber,
            date: inv.dateFormatted || inv.date,
            total: inv.totalAmount,
            productSubtotal: productSubtotal,
            extraChargesDesc: extraChargesDesc,
            extraChargesAmount: extraChargesAmount,
            invoiceType: inv.invoiceType
        };

        currentInvoiceData = invoiceData;
        currentHistoryData = {};
        currentExcelDownloadUrl = inv.downloadUrl;

        displayInvoiceModal(invoiceData, {}, inv.downloadUrl);

        if (autoPrint) {
            setTimeout(() => {
                printInvoice();
            }, 300);
        }

    } catch (e) {
        console.error('Error in previewInvoiceByNumber:', e);
        showToast('Error loading invoice preview', 'error');
    } finally {
        showLoading(false);
    }
}

/* ==========================================================================
   RESET ALL BUSINESS DATA CONTROLLER
   ========================================================================== */

function initResetModal() {
    const btnOpen = document.getElementById('btnOpenResetModal');
    const modal = document.getElementById('resetDataModal');
    const overlay = document.getElementById('resetModalOverlay');
    const btnClose = document.getElementById('btnCloseResetModal');
    const btnCancel = document.getElementById('btnCancelReset');
    const confirmInput = document.getElementById('confirmDeleteInput');
    const btnConfirm = document.getElementById('btnConfirmDelete');

    if (!modal) return;

    if (btnOpen) {
        btnOpen.addEventListener('click', openResetModal);
    }
    if (btnClose) btnClose.addEventListener('click', closeResetModal);
    if (btnCancel) btnCancel.addEventListener('click', closeResetModal);
    if (overlay) overlay.addEventListener('click', closeResetModal);

    if (confirmInput && btnConfirm) {
        confirmInput.addEventListener('input', function() {
            const val = this.value.trim();
            if (val === 'DELETE ALL DATA') {
                btnConfirm.disabled = false;
            } else {
                btnConfirm.disabled = true;
            }
        });
        
        confirmInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !btnConfirm.disabled) {
                executeResetAllData();
            }
        });

        btnConfirm.addEventListener('click', executeResetAllData);
    }
}

async function openResetModal() {
    const modal = document.getElementById('resetDataModal');
    const input = document.getElementById('confirmDeleteInput');
    const btnConfirm = document.getElementById('btnConfirmDelete');

    if (!modal) return;

    if (input) input.value = '';
    if (btnConfirm) {
        btnConfirm.disabled = true;
        btnConfirm.textContent = '🗑️ Permanently Delete All Data';
    }

    // Fetch dynamic preview stats
    try {
        const res = await fetch('/api/admin/reset-preview');
        const data = await res.json();
        if (data.success && data.preview) {
            const p = data.preview;
            const elInv = document.getElementById('dspInvoicesCount');
            const elCust = document.getElementById('dspCustomersCount');
            const elProd = document.getElementById('dspProductsCount');
            const elFold = document.getElementById('dspFoldersCount');

            if (elInv) elInv.textContent = p.invoicesCount || 0;
            if (elCust) elCust.textContent = p.customersCount || 0;
            if (elProd) elProd.textContent = p.productsCount || 0;
            if (elFold) elFold.textContent = p.foldersCount || 0;
        }
    } catch (e) {
        console.error('Error fetching reset preview:', e);
    }

    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
    if (input) setTimeout(() => input.focus(), 150);
}

function closeResetModal() {
    const modal = document.getElementById('resetDataModal');
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = '';
    }
}

async function executeResetAllData() {
    const input = document.getElementById('confirmDeleteInput');
    const btnConfirm = document.getElementById('btnConfirmDelete');

    if (!input || input.value.trim() !== 'DELETE ALL DATA') {
        showToast('Please type DELETE ALL DATA to confirm', 'warning');
        return;
    }

    if (btnConfirm) {
        btnConfirm.disabled = true;
        btnConfirm.textContent = '⏳ Wiping All Business Data...';
    }

    try {
        const res = await fetch('/api/admin/reset-all-data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                confirmation: 'DELETE ALL DATA'
            })
        });

        const data = await res.json();

        if (data.success) {
            // 1. Wipe local browser draft data
            try {
                localStorage.clear();
                sessionStorage.clear();
            } catch (storageErr) {
                console.warn('Storage clear error:', storageErr);
            }

            // 2. Clear current form inputs and state
            products = [];
            updateProductsList();
            updateTotal();
            if (shopNameInput) shopNameInput.value = '';
            if (areaInput) areaInput.value = '';
            if (productNameInput) productNameInput.value = '';
            if (quantityInput) quantityInput.value = '';
            if (priceInput) priceInput.value = '';
            const recSection = document.getElementById('recommendationsSection');
            if (recSection) recSection.style.display = 'none';
            const insightsSection = document.getElementById('insightsSection');
            if (insightsSection) insightsSection.style.display = 'none';

            // 3. Close Reset Modal
            closeResetModal();

            // 4. Show prominent success notification
            showToast('All business data permanently deleted! Ready for a clean start.', 'success', 5000);
            showStatus('System reset successfully. All invoices, customers, and recommendations have been cleared.', 'success');

            // 5. Navigate to Dashboard and reload clean zero data
            switchView('dashboard');
            loadDashboard('30d');

        } else {
            throw new Error(data.error || 'Failed to reset business data');
        }

    } catch (err) {
        console.error('Error executing reset:', err);
        showToast('Error resetting data: ' + err.message, 'error');
        if (btnConfirm) {
            btnConfirm.disabled = false;
            btnConfirm.textContent = '🗑️ Permanently Delete All Data';
        }
    }
}

// ========================================================
// SAFE DELETION CONTROLLERS & BULK ACTIONS
// ========================================================

// State tracking for deletion dialogs
let pendingDeleteInvoiceNumber = null;
let pendingBulkInvoiceNumbers = [];
let pendingDeleteCustomerName = null;
let pendingDeleteProductName = null;

// --- Event Delegation for Dynamic Invoices Table ---
function setupInvoicesTableDelegation() {
    const table = document.getElementById('invoicesFullTable');
    if (!table || table.dataset.delegationAttached === 'true') return;
    table.dataset.delegationAttached = 'true';

    // 1. Delegated Change for checkboxes
    table.addEventListener('change', function(e) {
        if (e.target && (e.target.classList.contains('invoice-row-checkbox') || e.target.classList.contains('invoice-checkbox'))) {
            if (e.target.id === 'selectAllInvoices') {
                handleSelectAllInvoices(e);
            } else {
                updateInvoicesBulkBar();
            }
        }
    });

    // 2. Delegated Click for edit buttons
    table.addEventListener('click', function(e) {
        const editBtn = e.target.closest('.action-edit, [data-action="edit-invoice"]');
        if (editBtn) {
            e.preventDefault();
            e.stopPropagation();
            const invNumber = (editBtn.getAttribute('data-invoice-number') || editBtn.getAttribute('data-id') || editBtn.getAttribute('data-invoice-id') || '').trim();
            if (invNumber) {
                openEditInvoiceModal(invNumber);
            }
            return;
        }

        const deleteBtn = e.target.closest('.action-delete, [data-action="delete-invoice"]');
        if (deleteBtn) {
            e.preventDefault();
            e.stopPropagation();
            const invNumber = (deleteBtn.getAttribute('data-invoice-number') || deleteBtn.getAttribute('data-id') || deleteBtn.getAttribute('data-invoice-id') || '').trim();
            const customer = deleteBtn.getAttribute('data-customer');
            const date = deleteBtn.getAttribute('data-date');
            const amount = parseFloat(deleteBtn.getAttribute('data-amount')) || 0;
            if (invNumber) {
                openDeleteInvoiceModal(invNumber, customer, date, amount);
            }
        }
    });
}

function setupRecentInvoicesDelegation() {
    const tbody = document.getElementById('dashRecentInvoicesBody');
    if (!tbody || tbody.dataset.delegationAttached === 'true') return;
    tbody.dataset.delegationAttached = 'true';

    tbody.addEventListener('click', function(e) {
        const editBtn = e.target.closest('.action-edit, [data-action="edit-invoice"]');
        if (editBtn) {
            e.preventDefault();
            e.stopPropagation();
            const invNumber = (editBtn.getAttribute('data-invoice-number') || editBtn.getAttribute('data-id') || '').trim();
            if (invNumber) {
                openEditInvoiceModal(invNumber);
            }
            return;
        }

        const deleteBtn = e.target.closest('.action-delete, [data-action="delete-invoice"]');
        if (deleteBtn) {
            e.preventDefault();
            e.stopPropagation();
            const invNumber = (deleteBtn.getAttribute('data-invoice-number') || deleteBtn.getAttribute('data-id') || '').trim();
            const customer = deleteBtn.getAttribute('data-customer');
            const date = deleteBtn.getAttribute('data-date');
            const amount = parseFloat(deleteBtn.getAttribute('data-amount')) || 0;
            if (invNumber) {
                openDeleteInvoiceModal(invNumber, customer, date, amount);
            }
        }
    });
}

// --- Invoices Selection & Bulk Action Bar ---
function updateInvoicesBulkBar() {
    const checkboxes = document.querySelectorAll('.invoice-row-checkbox:checked');
    const allCheckboxes = document.querySelectorAll('.invoice-row-checkbox');
    const bar = document.getElementById('invoicesBulkBar');
    const countEl = document.getElementById('bulkSelectedCount');
    const amountEl = document.getElementById('bulkSelectedAmount') || document.getElementById('bulkSelectedTotal');
    const selectAll = document.getElementById('selectAllInvoices');

    const count = checkboxes.length;
    if (count > 0) {
        let total = 0;
        checkboxes.forEach(cb => {
            const amt = parseFloat(cb.getAttribute('data-amount')) || 0;
            total += amt;
        });

        if (bar) bar.style.display = 'flex';
        // HTML is: <strong id="bulkSelectedCount">0</strong> selected (<strong id="bulkSelectedAmount">₹0.00</strong>)
        // Setting count directly avoids "2 invoices selected selected"
        if (countEl) countEl.textContent = count;
        if (amountEl) amountEl.textContent = `₹${formatIndianCurrency(total)}`;
    } else {
        if (bar) bar.style.display = 'none';
        if (countEl) countEl.textContent = '0';
        if (amountEl) amountEl.textContent = '₹0.00';
    }

    if (selectAll) {
        selectAll.checked = allCheckboxes.length > 0 && count === allCheckboxes.length;
        selectAll.indeterminate = count > 0 && count < allCheckboxes.length;
    }
}

function handleSelectAllInvoices(e) {
    const isChecked = e.target.checked;
    const checkboxes = document.querySelectorAll('.invoice-row-checkbox');
    checkboxes.forEach(cb => {
        cb.checked = isChecked;
    });
    updateInvoicesBulkBar();
}

function getSelectedInvoiceNumbers() {
    const checkboxes = document.querySelectorAll('.invoice-row-checkbox:checked');
    const ids = [];
    checkboxes.forEach(cb => {
        const val = (cb.value || cb.getAttribute('data-id') || cb.getAttribute('data-invoice-id') || '').trim();
        if (val && !ids.includes(val)) {
            ids.push(val);
        }
    });
    return ids;
}

// --- 1. Single Invoice Deletion ---
async function openDeleteInvoiceModal(invNumber, customer, date, amount) {
    if (!invNumber) return;
    const cleanNum = String(invNumber).trim();
    if (!cleanNum) return;

    pendingDeleteInvoiceNumber = cleanNum;

    const modal = document.getElementById('deleteInvoiceModal');
    const numEl = document.getElementById('delInvNumber');
    const custEl = document.getElementById('delInvCustomer');
    const dateEl = document.getElementById('delInvDate');
    const amtEl = document.getElementById('delInvAmount');

    if (numEl) numEl.textContent = cleanNum;
    if (custEl) custEl.textContent = customer || 'Loading...';
    if (dateEl) dateEl.textContent = date || 'Loading...';
    if (amtEl) amtEl.textContent = (typeof amount === 'number' && !isNaN(amount)) ? `₹${formatIndianCurrency(amount)}` : (amount || 'Loading...');

    if (modal) modal.style.display = 'flex';

    // If details were not provided, fetch invoice info from backend
    if (!customer || !amount || customer === 'Loading...') {
        try {
            const res = await fetch(`/api/invoices/${encodeURIComponent(cleanNum)}`);
            const data = await res.json();
            if (data.success && data.invoice) {
                const inv = data.invoice;
                if (custEl) custEl.textContent = inv.customerName || '-';
                if (dateEl) dateEl.textContent = inv.dateFormatted || inv.date || '-';
                if (amtEl) amtEl.textContent = `₹${formatIndianCurrency(inv.totalAmount || 0)}`;
            }
        } catch (e) {
            console.warn('Could not load invoice detail for deletion modal:', e);
        }
    }
}

function closeDeleteInvoiceModal() {
    const modal = document.getElementById('deleteInvoiceModal');
    if (modal) modal.style.display = 'none';
    pendingDeleteInvoiceNumber = null;
}

async function executeDeleteInvoice() {
    if (!pendingDeleteInvoiceNumber) return;

    const btnConfirm = document.getElementById('btnConfirmDeleteInvoice');
    const originalText = btnConfirm ? btnConfirm.textContent : '🗑️ Delete Invoice';
    if (btnConfirm) {
        btnConfirm.disabled = true;
        btnConfirm.textContent = 'Deleting...';
    }

    try {
        const invToDelete = pendingDeleteInvoiceNumber;
        const res = await fetch(`/api/invoices/${encodeURIComponent(invToDelete)}`, {
            method: 'DELETE'
        });
        const data = await res.json();

        if (data.success) {
            closeDeleteInvoiceModal();
            showToast(`Invoice ${invToDelete} deleted successfully.`, 'success');
            
            // Immediately remove the invoice row from the table DOM
            const row = document.querySelector(`tr[data-invoice-number="${invToDelete}"]`) || document.getElementById(`invoice-row-${invToDelete}`) || document.getElementById(`dash-invoice-row-${invToDelete}`);
            if (row) {
                row.remove();
            }

            // Update bulk bar & counts
            updateInvoicesBulkBar();

            // Refresh UI tables, badges, statistics and recommendations
            await updateAppBadges();
            await loadInvoicesTable();
            await loadCustomersTable();
            await loadProductsTable();
            await loadDashboard('30d');
            if (shopNameInput && shopNameInput.value.trim()) {
                loadCustomerRecommendations(shopNameInput.value.trim(), true);
            }
        } else {
            showToast(data.error || 'Failed to delete invoice.', 'error');
        }
    } catch (err) {
        console.error('Error deleting invoice:', err);
        showToast('Error deleting invoice: ' + err.message, 'error');
    } finally {
        if (btnConfirm) {
            btnConfirm.disabled = false;
            btnConfirm.textContent = originalText;
        }
    }
}

// --- 2. Bulk Invoice Deletion ---
function openBulkDeleteModal() {
    const selected = getSelectedInvoiceNumbers();
    if (!selected.length) {
        showToast('Please select at least one invoice to delete.', 'warning');
        return;
    }

    pendingBulkInvoiceNumbers = selected;
    let totalAmt = 0;
    document.querySelectorAll('.invoice-row-checkbox:checked').forEach(cb => {
        totalAmt += parseFloat(cb.getAttribute('data-amount')) || 0;
    });

    const modal = document.getElementById('bulkDeleteInvoicesModal');
    const countEl = document.getElementById('bulkDelCount');
    const totalEl = document.getElementById('bulkDelTotal');

    if (countEl) countEl.textContent = selected.length;
    if (totalEl) totalEl.textContent = `₹${formatIndianCurrency(totalAmt)}`;
    if (modal) modal.style.display = 'flex';
}

function closeBulkDeleteModal() {
    const modal = document.getElementById('bulkDeleteInvoicesModal');
    if (modal) modal.style.display = 'none';
    pendingBulkInvoiceNumbers = [];
}

async function executeBulkDeleteInvoices() {
    if (!pendingBulkInvoiceNumbers.length) return;

    const btnConfirm = document.getElementById('btnConfirmBulkDelete');
    const originalText = btnConfirm ? btnConfirm.textContent : '🗑️ Delete Selected Invoices';
    if (btnConfirm) {
        btnConfirm.disabled = true;
        btnConfirm.textContent = 'Deleting Invoices...';
    }

    try {
        const payload = {
            invoiceIds: pendingBulkInvoiceNumbers,
            invoice_numbers: pendingBulkInvoiceNumbers
        };

        const res = await fetch('/api/invoices/bulk-delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (data.success) {
            const deletedList = data.deletedInvoices || pendingBulkInvoiceNumbers;
            const deletedCount = data.deletedCount || data.deleted_count || deletedList.length;
            closeBulkDeleteModal();
            showToast(`Successfully deleted ${deletedCount} invoice(s).`, 'success');

            // Immediately remove rows from table DOM
            deletedList.forEach(num => {
                const row = document.querySelector(`tr[data-invoice-number="${num}"]`) || document.getElementById(`invoice-row-${num}`) || document.getElementById(`dash-invoice-row-${num}`);
                if (row) {
                    row.remove();
                }
            });

            // Reset selection and refresh
            pendingBulkInvoiceNumbers = [];
            const selectAll = document.getElementById('selectAllInvoices');
            if (selectAll) selectAll.checked = false;
            updateInvoicesBulkBar();

            // Refresh UI tables, badges, statistics and recommendations
            await updateAppBadges();
            await loadInvoicesTable();
            await loadCustomersTable();
            await loadProductsTable();
            await loadDashboard('30d');
            if (shopNameInput && shopNameInput.value.trim()) {
                loadCustomerRecommendations(shopNameInput.value.trim(), true);
            }
        } else {
            showToast(data.error || 'Failed to delete selected invoices.', 'error');
        }
    } catch (err) {
        console.error('Error in bulk invoice deletion:', err);
        showToast('Error deleting invoices: ' + err.message, 'error');
    } finally {
        if (btnConfirm) {
            btnConfirm.disabled = false;
            btnConfirm.textContent = originalText;
        }
    }
}

// --- 3. Customer Deletion (Two Choices) ---
async function openDeleteCustomerModal(customerName) {
    if (!customerName) return;
    pendingDeleteCustomerName = customerName;

    const modal = document.getElementById('deleteCustomerModal');
    const titleNameEl = document.getElementById('delCustTitleName');
    const nameEl = document.getElementById('delCustName');
    const targetMatchEl = document.getElementById('targetCustNameMatch');
    const inputConfirm = document.getElementById('confirmCustomerNameInput');
    const radioCatalog = document.getElementById('custDeleteModeCatalog');

    if (titleNameEl) titleNameEl.textContent = customerName;
    if (nameEl) nameEl.textContent = customerName;
    if (targetMatchEl) targetMatchEl.textContent = customerName;
    if (inputConfirm) inputConfirm.value = '';
    if (radioCatalog) radioCatalog.checked = true;

    updateCustomerDeleteChoiceUI();
    if (modal) modal.style.display = 'flex';

    // Fetch customer deletion preview
    try {
        const res = await fetch(`/api/customers/${encodeURIComponent(customerName)}/delete-preview`);
        const data = await res.json();
        if (data.success) {
            const countEl = document.getElementById('delCustInvoiceCount');
            const spendEl = document.getElementById('delCustTotalSpend');
            const folderInvsEl = document.getElementById('delCustFolderInvsCount');
            const folderPreviewEl = document.getElementById('delCustFolderPreview');

            if (countEl) countEl.textContent = data.invoice_count || 0;
            if (spendEl) spendEl.textContent = `₹${formatIndianCurrency(data.total_spent || 0)}`;
            if (folderInvsEl) folderInvsEl.textContent = data.invoice_count || 0;
            if (folderPreviewEl) folderPreviewEl.textContent = data.customer_folder || `Invoice Storage/${customerName}`;
        }
    } catch (err) {
        console.warn('Could not load customer delete preview:', err);
    }
}

function updateCustomerDeleteChoiceUI() {
    const isPermanent = document.getElementById('custDeleteModePermanent')?.checked;
    const card1 = document.getElementById('custChoice1Card');
    const card2 = document.getElementById('custChoice2Card');
    const confirmBox = document.getElementById('custPermanentConfirmBox');
    const btnConfirm = document.getElementById('btnConfirmDeleteCustomer');

    if (card1 && card2) {
        if (isPermanent) {
            card1.classList.remove('active');
            card2.classList.add('active');
            if (confirmBox) confirmBox.style.display = 'block';
            if (btnConfirm) btnConfirm.textContent = '🗑️ Permanently Delete Customer';
        } else {
            card1.classList.add('active');
            card2.classList.remove('active');
            if (confirmBox) confirmBox.style.display = 'none';
            if (btnConfirm) btnConfirm.textContent = 'Remove from Suggestions';
        }
    }
}

function closeDeleteCustomerModal() {
    const modal = document.getElementById('deleteCustomerModal');
    if (modal) modal.style.display = 'none';
    pendingDeleteCustomerName = null;
}

async function executeDeleteCustomer() {
    if (!pendingDeleteCustomerName) return;

    const isPermanent = document.getElementById('custDeleteModePermanent')?.checked;
    const customerName = pendingDeleteCustomerName;

    if (isPermanent) {
        const inputVal = document.getElementById('confirmCustomerNameInput')?.value.trim() || '';
        if (inputVal !== customerName) {
            showToast(`Customer name does not match. Please type "${customerName}" exactly to confirm.`, 'error');
            return;
        }
    }

    const btnConfirm = document.getElementById('btnConfirmDeleteCustomer');
    if (btnConfirm) {
        btnConfirm.disabled = true;
        btnConfirm.textContent = 'Processing...';
    }

    try {
        const endpoint = isPermanent
            ? `/api/customers/${encodeURIComponent(customerName)}/all-data`
            : `/api/customers/${encodeURIComponent(customerName)}`;

        const fetchOptions = {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' }
        };
        if (isPermanent) {
            fetchOptions.body = JSON.stringify({ confirmation: customerName });
        }

        const res = await fetch(endpoint, fetchOptions);
        const data = await res.json();

        if (data.success) {
            closeDeleteCustomerModal();
            closeCustomerModal(); // In case detail drawer was open
            showToast(data.message || `Customer "${customerName}" deleted successfully.`, 'success');

            updateAppBadges();
            loadCustomersTable();
            if (isPermanent) {
                loadInvoicesTable();
                loadProductsTable();
                loadDashboard('30d');
            }
        } else {
            showToast(data.error || 'Failed to delete customer.', 'error');
        }
    } catch (err) {
        console.error('Error deleting customer:', err);
        showToast('Error deleting customer: ' + err.message, 'error');
    } finally {
        if (btnConfirm) {
            btnConfirm.disabled = false;
            updateCustomerDeleteChoiceUI();
        }
    }
}

// --- 4. Product Deletion (Two Choices) ---
async function openDeleteProductModal(productName) {
    if (!productName) return;
    pendingDeleteProductName = productName;

    const modal = document.getElementById('deleteProductModal');
    const titleNameEl = document.getElementById('delProdTitleName');
    const nameEl = document.getElementById('delProdName');
    const inputConfirm = document.getElementById('confirmProdDeleteInput');
    const radioCatalog = document.getElementById('prodDeleteModeCatalog');

    if (titleNameEl) titleNameEl.textContent = productName;
    if (nameEl) nameEl.textContent = productName;
    if (inputConfirm) inputConfirm.value = '';
    if (radioCatalog) radioCatalog.checked = true;

    updateProductDeleteChoiceUI();
    if (modal) modal.style.display = 'flex';

    // Fetch product deletion preview
    try {
        const res = await fetch(`/api/products/${encodeURIComponent(productName)}/delete-preview`);
        const data = await res.json();
        if (data.success) {
            const countEl = document.getElementById('delProdInvCount');
            const qtyEl = document.getElementById('delProdQty');
            const salesEl = document.getElementById('delProdSales');
            const affectedList = document.getElementById('prodAffectedInvoicesList');

            if (countEl) countEl.textContent = data.affected_invoices_count || 0;
            if (qtyEl) qtyEl.textContent = data.total_quantity_sold || 0;
            if (salesEl) salesEl.textContent = `₹${formatIndianCurrency(data.total_sales || 0)}`;

            if (affectedList) {
                const invs = data.affected_invoices || [];
                if (invs.length) {
                    affectedList.innerHTML = invs.slice(0, 5).map(inv => `
                        <div class="aip-item">
                            <span class="aip-inv-num">${escapeHtml(inv.invoice_number)}</span>
                            <span class="aip-inv-cust">${escapeHtml(inv.customer_name)}</span>
                            <span class="aip-inv-total">₹${formatIndianCurrency(inv.line_total || 0)}</span>
                        </div>
                    `).join('') + (invs.length > 5 ? `<div style="font-size:0.75rem; color:#64748B; padding:4px 8px;">+ ${invs.length - 5} more invoice(s)</div>` : '');
                } else {
                    affectedList.innerHTML = '<div style="font-size:0.75rem; color:#64748B; padding:4px 8px;">No historical invoices contain this product.</div>';
                }
            }
        }
    } catch (err) {
        console.warn('Could not load product delete preview:', err);
    }
}

function updateProductDeleteChoiceUI() {
    const isPermanent = document.getElementById('prodDeleteModePermanent')?.checked;
    const card1 = document.getElementById('prodChoice1Card');
    const card2 = document.getElementById('prodChoice2Card');
    const confirmBox = document.getElementById('prodPermanentConfirmBox');
    const btnConfirm = document.getElementById('btnConfirmDeleteProduct');

    if (card1 && card2) {
        if (isPermanent) {
            card1.classList.remove('active');
            card2.classList.add('active');
            if (confirmBox) confirmBox.style.display = 'block';
            if (btnConfirm) btnConfirm.textContent = '🗑️ Permanently Delete Product Data';
        } else {
            card1.classList.add('active');
            card2.classList.remove('active');
            if (confirmBox) confirmBox.style.display = 'none';
            if (btnConfirm) btnConfirm.textContent = 'Remove from Autocomplete';
        }
    }
}

function closeDeleteProductModal() {
    const modal = document.getElementById('deleteProductModal');
    if (modal) modal.style.display = 'none';
    pendingDeleteProductName = null;
}

async function executeDeleteProduct() {
    if (!pendingDeleteProductName) return;

    const isPermanent = document.getElementById('prodDeleteModePermanent')?.checked;
    const productName = pendingDeleteProductName;

    if (isPermanent) {
        const inputVal = document.getElementById('confirmProdDeleteInput')?.value.trim().toUpperCase() || '';
        if (inputVal !== 'DELETE PRODUCT DATA') {
            showToast('Please type "DELETE PRODUCT DATA" to confirm.', 'error');
            return;
        }
    }

    const btnConfirm = document.getElementById('btnConfirmDeleteProduct');
    if (btnConfirm) {
        btnConfirm.disabled = true;
        btnConfirm.textContent = 'Processing...';
    }

    try {
        const endpoint = isPermanent
            ? `/api/products/${encodeURIComponent(productName)}/all-data`
            : `/api/products/${encodeURIComponent(productName)}`;

        const fetchOptions = {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' }
        };
        if (isPermanent) {
            fetchOptions.body = JSON.stringify({ confirmation: 'DELETE PRODUCT DATA' });
        }

        const res = await fetch(endpoint, fetchOptions);
        const data = await res.json();

        if (data.success) {
            closeDeleteProductModal();
            closeProductModal(); // In case drawer was open
            showToast(data.message || `Product "${productName}" deleted successfully.`, 'success');

            updateAppBadges();
            loadProductsTable();
            if (isPermanent) {
                loadInvoicesTable();
                loadCustomersTable();
                loadDashboard('30d');
            }
        } else {
            showToast(data.error || 'Failed to delete product.', 'error');
        }
    } catch (err) {
        console.error('Error deleting product:', err);
        showToast('Error deleting product: ' + err.message, 'error');
    } finally {
        if (btnConfirm) {
            btnConfirm.disabled = false;
            updateProductDeleteChoiceUI();
        }
    }
}

// Helper to update sidebar badge counters
async function updateAppBadges() {
    try {
        const res = await fetch('/api/dashboard?range=all');
        const data = await res.json();
        if (data.success && data.metrics) {
            const bInv = document.getElementById('badgeInvoiceCount');
            const bCust = document.getElementById('badgeCustomerCount');
            const bProd = document.getElementById('badgeProductCount');
            if (bInv) bInv.textContent = data.metrics.allTimeInvoices !== undefined ? data.metrics.allTimeInvoices : (data.metrics.totalInvoices || 0);
            if (bCust) bCust.textContent = data.metrics.totalCustomers || 0;
            if (bProd) bProd.textContent = data.metrics.totalProducts || 0;
        }
    } catch (e) {
        console.warn('Could not update sidebar badges:', e);
    }
}

// Master Delete Modals Initializer
function initDeleteModals() {
    // 1. Single Invoice Modal Listeners
    const btnCancelDelInv = document.getElementById('btnCancelDeleteInvoice');
    const btnCloseDelInv = document.getElementById('btnCloseDeleteInvoiceModal');
    const overlayDelInv = document.getElementById('deleteInvoiceModalOverlay');
    const btnConfirmDelInv = document.getElementById('btnConfirmDeleteInvoice');

    if (btnCancelDelInv) btnCancelDelInv.addEventListener('click', closeDeleteInvoiceModal);
    if (btnCloseDelInv) btnCloseDelInv.addEventListener('click', closeDeleteInvoiceModal);
    if (overlayDelInv) overlayDelInv.addEventListener('click', closeDeleteInvoiceModal);
    if (btnConfirmDelInv) btnConfirmDelInv.addEventListener('click', executeDeleteInvoice);

    // 2. Bulk Invoices Modal & Selection Listeners
    const selectAllInv = document.getElementById('selectAllInvoices');
    if (selectAllInv) selectAllInv.addEventListener('change', handleSelectAllInvoices);

    const btnOpenBulkDel = document.getElementById('btnOpenBulkDeleteModal') || document.getElementById('btnBulkDeleteInvoices');
    if (btnOpenBulkDel) btnOpenBulkDel.addEventListener('click', openBulkDeleteModal);

    const btnCancelBulkSelect = document.getElementById('btnCancelBulkSelection');
    if (btnCancelBulkSelect) {
        btnCancelBulkSelect.addEventListener('click', () => {
            const checkboxes = document.querySelectorAll('.invoice-row-checkbox');
            checkboxes.forEach(cb => { cb.checked = false; });
            const selectAll = document.getElementById('selectAllInvoices');
            if (selectAll) selectAll.checked = false;
            updateInvoicesBulkBar();
        });
    }

    const btnCancelBulk = document.getElementById('btnCancelBulkDelete');
    const btnCloseBulk = document.getElementById('btnCloseBulkDeleteModal');
    const overlayBulk = document.getElementById('bulkDeleteInvoicesOverlay');
    const btnConfirmBulk = document.getElementById('btnConfirmBulkDelete');

    if (btnCancelBulk) btnCancelBulk.addEventListener('click', closeBulkDeleteModal);
    if (btnCloseBulk) btnCloseBulk.addEventListener('click', closeBulkDeleteModal);
    if (overlayBulk) overlayBulk.addEventListener('click', closeBulkDeleteModal);
    if (btnConfirmBulk) btnConfirmBulk.addEventListener('click', executeBulkDeleteInvoices);

    // Attach dynamic table event delegations
    setupInvoicesTableDelegation();
    setupRecentInvoicesDelegation();

    // 3. Customer Delete Modal Listeners
    const btnCancelDelCust = document.getElementById('btnCancelDeleteCustomer');
    const btnCloseDelCust = document.getElementById('btnCloseDeleteCustomerModal');
    const overlayDelCust = document.getElementById('deleteCustomerModalOverlay');
    const btnConfirmDelCust = document.getElementById('btnConfirmDeleteCustomer');
    const radioCustCatalog = document.getElementById('custDeleteModeCatalog');
    const radioCustPerm = document.getElementById('custDeleteModePermanent');

    if (btnCancelDelCust) btnCancelDelCust.addEventListener('click', closeDeleteCustomerModal);
    if (btnCloseDelCust) btnCloseDelCust.addEventListener('click', closeDeleteCustomerModal);
    if (overlayDelCust) overlayDelCust.addEventListener('click', closeDeleteCustomerModal);
    if (btnConfirmDelCust) btnConfirmDelCust.addEventListener('click', executeDeleteCustomer);
    if (radioCustCatalog) radioCustCatalog.addEventListener('change', updateCustomerDeleteChoiceUI);
    if (radioCustPerm) radioCustPerm.addEventListener('change', updateCustomerDeleteChoiceUI);

    // 4. Product Delete Modal Listeners
    const btnCancelDelProd = document.getElementById('btnCancelDeleteProduct');
    const btnCloseDelProd = document.getElementById('btnCloseDeleteProductModal');
    const overlayDelProd = document.getElementById('deleteProductModalOverlay');
    const btnConfirmDelProd = document.getElementById('btnConfirmDeleteProduct');
    const radioProdCatalog = document.getElementById('prodDeleteModeCatalog');
    const radioProdPerm = document.getElementById('prodDeleteModePermanent');

    if (btnCancelDelProd) btnCancelDelProd.addEventListener('click', closeDeleteProductModal);
    if (btnCloseDelProd) btnCloseDelProd.addEventListener('click', closeDeleteProductModal);
    if (overlayDelProd) overlayDelProd.addEventListener('click', closeDeleteProductModal);
    if (btnConfirmDelProd) btnConfirmDelProd.addEventListener('click', executeDeleteProduct);
    if (radioProdCatalog) radioProdCatalog.addEventListener('change', updateProductDeleteChoiceUI);
    if (radioProdPerm) radioProdPerm.addEventListener('change', updateProductDeleteChoiceUI);

    // Expose functions globally for table HTML onclick handlers and console testing
    window.openDeleteInvoiceModal = openDeleteInvoiceModal;
    window.closeDeleteInvoiceModal = closeDeleteInvoiceModal;
    window.executeDeleteInvoice = executeDeleteInvoice;
    window.openBulkDeleteModal = openBulkDeleteModal;
    window.closeBulkDeleteModal = closeBulkDeleteModal;
    window.executeBulkDeleteInvoices = executeBulkDeleteInvoices;
    window.openDeleteCustomerModal = openDeleteCustomerModal;
    window.openDeleteProductModal = openDeleteProductModal;
    window.updateInvoicesBulkBar = updateInvoicesBulkBar;
    window.getSelectedInvoiceNumbers = getSelectedInvoiceNumbers;
    window.setupInvoicesTableDelegation = setupInvoicesTableDelegation;
    window.updateAppBadges = updateAppBadges;
}

// ========================================================
// EDIT INVOICE CONTROLLER & MODAL
// ========================================================

let pendingEditInvoiceNumber = null;
let editRowCounter = 0;

// Open Edit Invoice Modal and populate with live saved invoice data
async function openEditInvoiceModal(invNumber) {
    if (!invNumber) return;
    const cleanNum = String(invNumber).trim();
    if (!cleanNum) return;

    pendingEditInvoiceNumber = cleanNum;

    const modal = document.getElementById('editInvoiceModal');
    const badge = document.getElementById('editModalInvoiceNumBadge');
    const custInput = document.getElementById('editCustomerName');
    const areaInput = document.getElementById('editCustomerArea');
    const typeSelect = document.getElementById('editInvoiceType');
    const tbody = document.getElementById('editProductsTableBody');

    if (badge) badge.textContent = cleanNum;
    if (custInput) custInput.value = 'Loading...';
    if (areaInput) areaInput.value = '';
    if (tbody) tbody.innerHTML = '<tr><td colspan="5" class="loading-state" style="text-align:center; padding:20px; color:#64748B;">Loading invoice data...</td></tr>';

    if (modal) modal.style.display = 'flex';

    try {
        const res = await fetch(`/api/invoices/${encodeURIComponent(cleanNum)}`);
        const data = await res.json();

        if (!data.success || !data.invoice) {
            throw new Error(data.error || 'Failed to fetch invoice details');
        }

        const inv = data.invoice;
        if (custInput) custInput.value = inv.customerName || '';
        if (areaInput) areaInput.value = inv.area || '';
        if (typeSelect) typeSelect.value = inv.invoiceType || 'current';

        // Load saved extra charge values (legacy invoices open with empty description and 0.00)
        const editExtraDescInput = document.getElementById('editExtraChargesDesc');
        const editExtraAmtInput = document.getElementById('editExtraChargesAmount');
        if (editExtraDescInput) editExtraDescInput.value = inv.extraChargesDesc || '';
        if (editExtraAmtInput) editExtraAmtInput.value = Number(inv.extraChargesAmount || 0).toFixed(2);

        // Render product rows
        renderEditProductRows(inv.products || []);

        // Initialize autocomplete on customer input if not already done
        initEditCustomerAutocomplete();

    } catch (err) {
        console.error('Error opening edit invoice modal:', err);
        showToast('Error loading invoice: ' + err.message, 'error');
        closeEditInvoiceModal();
    }
}

// Close Edit Invoice Modal
function closeEditInvoiceModal() {
    const modal = document.getElementById('editInvoiceModal');
    if (modal) modal.style.display = 'none';
    pendingEditInvoiceNumber = null;
}

// Render all product rows in edit modal
function renderEditProductRows(productsList) {
    const tbody = document.getElementById('editProductsTableBody');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (!productsList || productsList.length === 0) {
        addEditProductRow({ name: '', quantity: 1, price: 0 });
    } else {
        productsList.forEach(item => {
            addEditProductRow(item);
        });
    }
    calculateEditTotals();
}

// Add a single product row in edit modal
function addEditProductRow(item = {}) {
    const tbody = document.getElementById('editProductsTableBody');
    if (!tbody) return;

    editRowCounter++;
    const rowId = `edit-prod-row-${editRowCounter}`;
    const name = item.name || item.product_name || item.productName || '';
    const qty = parseInt(item.quantity) || 1;
    const price = parseFloat(item.price !== undefined ? item.price : (item.unit_price !== undefined ? item.unit_price : item.unitPrice)) || 0;
    const lineTotal = Math.round(qty * price * 100) / 100;

    const tr = document.createElement('tr');
    tr.className = 'edit-prod-row';
    tr.id = rowId;
    tr.innerHTML = `
        <td>
            <div class="autocomplete-wrapper" style="position: relative;">
                <input type="text" class="edit-prod-input edit-prod-name" value="${escapeHtml(name)}" placeholder="Enter product name" autocomplete="off" required>
                <div class="autocomplete-dropdown edit-prod-autocomplete" style="display: none;"></div>
            </div>
        </td>
        <td style="text-align: center;">
            <input type="number" class="edit-qty-input edit-prod-qty" value="${qty}" min="1" step="1" required style="width: 70px; margin: 0 auto; text-align: center;">
        </td>
        <td style="text-align: right;">
            <input type="number" class="edit-price-input edit-prod-price" value="${price.toFixed(2)}" min="0" step="0.01" required style="width: 105px; margin-left: auto; text-align: right;">
        </td>
        <td style="text-align: right; vertical-align: middle;">
            <span class="edit-line-total">₹${formatIndianCurrency(lineTotal)}</span>
        </td>
        <td style="text-align: center; vertical-align: middle;">
            <button type="button" class="btn-remove-row edit-remove-btn" title="Remove Product">✕</button>
        </td>
    `;

    tbody.appendChild(tr);

    const qtyInput = tr.querySelector('.edit-prod-qty');
    const priceInput = tr.querySelector('.edit-prod-price');
    const nameInput = tr.querySelector('.edit-prod-name');
    const dropdown = tr.querySelector('.edit-prod-autocomplete');
    const removeBtn = tr.querySelector('.edit-remove-btn');

    const updateRowTotal = () => {
        const q = parseFloat(qtyInput.value) || 0;
        const p = parseFloat(priceInput.value) || 0;
        const lt = Math.round(q * p * 100) / 100;
        const totalCell = tr.querySelector('.edit-line-total');
        if (totalCell) totalCell.textContent = `₹${formatIndianCurrency(lt)}`;
        calculateEditTotals();
    };

    qtyInput.addEventListener('input', updateRowTotal);
    priceInput.addEventListener('input', updateRowTotal);

    removeBtn.addEventListener('click', () => {
        tr.remove();
        if (!tbody.querySelectorAll('.edit-prod-row').length) {
            addEditProductRow({ name: '', quantity: 1, price: 0 });
        }
        calculateEditTotals();
    });

    // Wire product autocomplete for this line
    if (nameInput && dropdown) {
        setupAutocomplete({
            inputEl: nameInput,
            dropdownEl: dropdown,
            fetchUrl: '/api/autocomplete/products?q=',
            dataKey: 'products',
            renderItem: (prod, idx) => {
                const hasP = prod.price !== undefined && prod.price !== null && Number(prod.price) > 0;
                const priceFmt = hasP ? `₹${Number(prod.price).toFixed(2)}` : '';
                return `
                    <div class="autocomplete-item" data-index="${idx}">
                        <div class="autocomplete-info">
                            <span class="autocomplete-name">${escapeHtml(prod.name)}</span>
                            ${hasP ? `<span class="autocomplete-sep">—</span><span class="autocomplete-price">${priceFmt}</span>` : ''}
                        </div>
                        ${prod.frequency > 1 ? `<span class="autocomplete-tag">${prod.frequency} sold</span>` : ''}
                    </div>
                `;
            },
            onSelect: (prod) => {
                nameInput.value = prod.name;
                if (prod.price !== undefined && prod.price !== null && Number(prod.price) > 0) {
                    priceInput.value = Number(prod.price).toFixed(2);
                }
                updateRowTotal();
                qtyInput.focus();
            }
        });
    }

    calculateEditTotals();
}

// Calculate edit modal grand total and item counts with Extra Charges
function calculateEditTotals() {
    const rows = document.querySelectorAll('#editProductsTableBody .edit-prod-row');
    let productSubtotal = 0;
    let totalQty = 0;
    let count = 0;

    rows.forEach(tr => {
        const qty = parseFloat(tr.querySelector('.edit-prod-qty')?.value) || 0;
        const price = parseFloat(tr.querySelector('.edit-prod-price')?.value) || 0;
        const lineTotal = Math.round(qty * price * 100) / 100;
        productSubtotal += lineTotal;
        totalQty += qty;
        count++;
    });

    const extraAmtInput = document.getElementById('editExtraChargesAmount');
    const extraDescInput = document.getElementById('editExtraChargesDesc');
    const extraAmt = parseFloat(extraAmtInput?.value) || 0;
    const extraDesc = (extraDescInput?.value || '').trim() || 'Extra';

    const grandTotal = Math.round((productSubtotal + (extraAmt > 0 ? extraAmt : 0)) * 100) / 100;

    const totalBadge = document.getElementById('editGrandTotalAmount');
    const countBadge = document.getElementById('editItemsCountBadge');
    const qtyBadge = document.getElementById('editTotalQtyBadge');
    const subtotalBadge = document.getElementById('editProductSubtotalAmount');
    const extraSummaryRow = document.getElementById('editExtraChargesSummaryRow');
    const extraSummaryLabel = document.getElementById('editExtraChargesSummaryLabel');
    const extraSummaryAmount = document.getElementById('editExtraChargesSummaryAmount');

    if (subtotalBadge) subtotalBadge.textContent = `₹${formatIndianCurrency(productSubtotal)}`;
    if (extraSummaryRow) {
        if (extraAmt > 0) {
            extraSummaryRow.style.display = 'inline-flex';
            if (extraSummaryLabel) extraSummaryLabel.textContent = `${extraDesc}:`;
            if (extraSummaryAmount) extraSummaryAmount.textContent = `+₹${formatIndianCurrency(extraAmt)}`;
        } else {
            extraSummaryRow.style.display = 'none';
        }
    }

    if (totalBadge) totalBadge.textContent = `₹${formatIndianCurrency(grandTotal)}`;
    if (countBadge) countBadge.textContent = `${count} product${count !== 1 ? 's' : ''}`;
    if (qtyBadge) qtyBadge.textContent = `${totalQty} total qty`;
}

// Initialize customer autocomplete in edit modal
function initEditCustomerAutocomplete() {
    const custInput = document.getElementById('editCustomerName');
    const custDropdown = document.getElementById('editCustomerAutocomplete');
    const areaInput = document.getElementById('editCustomerArea');
    if (!custInput || !custDropdown || custInput.dataset.autocompleteAttached === 'true') return;
    custInput.dataset.autocompleteAttached = 'true';

    setupAutocomplete({
        inputEl: custInput,
        dropdownEl: custDropdown,
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
            custInput.value = cust.shopName;
            if (cust.area && areaInput) {
                areaInput.value = cust.area;
            }
        }
    });
}

// Execute Save Changes for Edited Invoice
async function executeSaveInvoiceEdit() {
    if (!pendingEditInvoiceNumber) return;

    const custName = document.getElementById('editCustomerName')?.value.trim() || '';
    const custArea = document.getElementById('editCustomerArea')?.value.trim() || '';
    const invType = document.getElementById('editInvoiceType')?.value || 'current';

    if (!custName) {
        showToast('Please enter customer / shop name.', 'error');
        document.getElementById('editCustomerName')?.focus();
        return;
    }
    if (!custArea) {
        showToast('Please enter area / location.', 'error');
        document.getElementById('editCustomerArea')?.focus();
        return;
    }

    const rows = document.querySelectorAll('#editProductsTableBody .edit-prod-row');
    if (!rows.length) {
        showToast('Please add at least one product row.', 'error');
        return;
    }

    const products = [];
    let hasInvalid = false;
    rows.forEach((tr, idx) => {
        const name = tr.querySelector('.edit-prod-name')?.value.trim() || '';
        const qty = parseInt(tr.querySelector('.edit-prod-qty')?.value, 10);
        const price = parseFloat(tr.querySelector('.edit-prod-price')?.value);

        if (!name) {
            showToast(`Product name is required on row ${idx + 1}.`, 'error');
            hasInvalid = true;
            return;
        }
        if (!qty || qty <= 0) {
            showToast(`Invalid quantity for "${name}". Must be at least 1.`, 'error');
            hasInvalid = true;
            return;
        }
        if (isNaN(price) || price < 0) {
            showToast(`Invalid unit price for "${name}". Must be 0 or more.`, 'error');
            hasInvalid = true;
            return;
        }

        products.push({
            name: name,
            quantity: qty,
            price: price,
            total: Math.round(qty * price * 100) / 100
        });
    });

    if (hasInvalid) return;

    const extraChargesDesc = (document.getElementById('editExtraChargesDesc')?.value || '').trim();
    const rawExtraAmt = document.getElementById('editExtraChargesAmount')?.value;
    const extraChargesAmount = parseFloat(rawExtraAmt) || 0.0;
    if (extraChargesAmount < 0) {
        showToast('Extra charges amount cannot be negative.', 'error');
        document.getElementById('editExtraChargesAmount')?.focus();
        return;
    }

    const btnSave = document.getElementById('btnSaveEditInvoice');
    const originalText = btnSave ? btnSave.textContent : '💾 Save Changes';
    if (btnSave) {
        btnSave.disabled = true;
        btnSave.textContent = 'Saving Changes...';
    }

    try {
        const payload = {
            customer: {
                shopName: custName,
                area: custArea
            },
            customerName: custName,
            area: custArea,
            invoiceType: invType,
            products: products,
            extraChargesDesc: extraChargesDesc,
            extraChargesAmount: extraChargesAmount
        };

        const res = await fetch(`/api/invoices/${encodeURIComponent(pendingEditInvoiceNumber)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (data.success) {
            const updatedInvNum = pendingEditInvoiceNumber;
            closeEditInvoiceModal();
            showToast(`Invoice ${updatedInvNum} updated successfully!`, 'success');

            // Refresh UI tables, badges, statistics and recommendations
            await updateAppBadges();
            await loadInvoicesTable();
            await loadCustomersTable();
            await loadProductsTable();
            await loadDashboard('30d');
            if (shopNameInput && shopNameInput.value.trim()) {
                loadCustomerRecommendations(shopNameInput.value.trim(), true);
            }
        } else {
            showToast(data.error || 'Failed to update invoice.', 'error');
        }
    } catch (err) {
        console.error('Error updating invoice:', err);
        showToast('Error updating invoice: ' + err.message, 'error');
    } finally {
        if (btnSave) {
            btnSave.disabled = false;
            btnSave.textContent = originalText;
        }
    }
}

// Initialize Edit Invoice Modal Listeners
function initEditInvoiceModal() {
    const btnCancel = document.getElementById('btnCancelEditInvoice');
    const btnClose = document.getElementById('btnCloseEditInvoiceModal');
    const overlay = document.getElementById('editInvoiceModalOverlay');
    const btnSave = document.getElementById('btnSaveEditInvoice');
    const btnAddRow = document.getElementById('btnAddEditProductRow');
    const editExtraAmt = document.getElementById('editExtraChargesAmount');
    const editExtraDesc = document.getElementById('editExtraChargesDesc');

    if (btnCancel) btnCancel.addEventListener('click', closeEditInvoiceModal);
    if (btnClose) btnClose.addEventListener('click', closeEditInvoiceModal);
    if (overlay) overlay.addEventListener('click', closeEditInvoiceModal);
    if (btnSave) btnSave.addEventListener('click', executeSaveInvoiceEdit);
    if (btnAddRow) btnAddRow.addEventListener('click', () => addEditProductRow({ name: '', quantity: 1, price: 0 }));
    if (editExtraAmt) editExtraAmt.addEventListener('input', calculateEditTotals);
    if (editExtraDesc) editExtraDesc.addEventListener('input', calculateEditTotals);

    // Global expose
    window.openEditInvoiceModal = openEditInvoiceModal;
    window.closeEditInvoiceModal = closeEditInvoiceModal;
    window.addEditProductRow = addEditProductRow;
    window.calculateEditTotals = calculateEditTotals;
    window.executeSaveInvoiceEdit = executeSaveInvoiceEdit;
}

// --- PWA Installation & Service Worker ---
function initPwaInstall() {
    if ('serviceWorker' in navigator) {
        window.addEventListener('load', () => {
            navigator.serviceWorker.register('/sw.js')
                .then(reg => console.log('✅ PWA ServiceWorker active:', reg.scope))
                .catch(err => console.warn('PWA ServiceWorker notice:', err));
        });
    }

    let deferredPrompt = null;
    const btnInstall = document.getElementById('btnInstallPwa');
    if (!btnInstall) return;

    const isStandalone = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone;

    if (isStandalone) {
        btnInstall.style.display = 'flex';
        btnInstall.classList.add('installed');
        btnInstall.innerHTML = '<span class="btn-icon">✓</span> <span class="btn-text">App Active</span>';
        btnInstall.disabled = true;
        return;
    }

    btnInstall.style.display = 'flex';

    window.addEventListener('beforeinstallprompt', (e) => {
        e.preventDefault();
        deferredPrompt = e;
        btnInstall.style.display = 'flex';
    });

    btnInstall.addEventListener('click', async () => {
        if (deferredPrompt) {
            deferredPrompt.prompt();
            const { outcome } = await deferredPrompt.userChoice;
            if (outcome === 'accepted') {
                btnInstall.classList.add('installed');
                btnInstall.innerHTML = '<span class="btn-icon">✓</span> <span class="btn-text">Installed</span>';
                btnInstall.disabled = true;
            }
            deferredPrompt = null;
        } else {
            alert('📱 To Install as an App:\n\n• Windows / Mac (Chrome & Edge): Look for the "Install" icon (⊕ or screen) on the right side of your address bar.\n• iPhone / iPad (Safari): Tap the Share button (square with arrow) and select "Add to Home Screen".\n• Android (Chrome): Tap the three dots (⋮) menu and choose "Install App" or "Add to Home Screen".');
        }
    });

    window.addEventListener('appinstalled', () => {
        btnInstall.classList.add('installed');
        btnInstall.innerHTML = '<span class="btn-icon">✓</span> <span class="btn-text">Installed</span>';
        btnInstall.disabled = true;
    });
}

// ========================================================
// LIVE SQLITE DATABASE BROWSER CONTROLLER
// ========================================================
let currentSelectedDbTable = 'invoices';
let currentDbRawRows = [];
let currentDbColumns = [];

async function loadDatabaseBrowser(tableName = null) {
    if (tableName) currentSelectedDbTable = tableName;
    const pillsContainer = document.getElementById('dbTablePills');
    const tbody = document.getElementById('dbTableBody');
    const tableNameEl = document.getElementById('dbActiveTableName');
    const rowCountEl = document.getElementById('dbActiveRowCount');

    if (tbody) {
        tbody.innerHTML = '<tr><td colspan="15" class="loading-state" style="padding:24px; text-align:center;">Loading live table data...</td></tr>';
    }

    try {
        const url = `/api/admin/raw-database?table=${encodeURIComponent(currentSelectedDbTable)}`;
        console.log(`[REQUEST] GET ${url}`);
        const res = await fetch(url);
        console.log(`[RESPONSE] GET ${url} -> ${res.status} ${res.statusText}`);
        const data = await res.json();
        console.log(`[BODY] /api/admin/raw-database: table=${data.selected_table}, rows=${data.total_rows}, success=${data.success}`);
        if (!data.success) throw new Error(data.error || 'Failed to fetch database data');

        const dbTitleEl = document.getElementById('dbBrowserTitle');
        const dbSubtitleEl = document.getElementById('dbBrowserSubtitle');
        const statusTextEl = document.getElementById('systemStatusText');
        if (data.engine === 'PostgreSQL') {
            if (dbTitleEl) dbTitleEl.textContent = '🗄️ PostgreSQL Database Browser';
            if (dbSubtitleEl) dbSubtitleEl.textContent = 'Render Production Cloud Database (PostgreSQL: bbExcel-postgre)';
            if (statusTextEl) statusTextEl.textContent = 'PostgreSQL Cloud DB Active';
        } else {
            if (dbTitleEl) dbTitleEl.textContent = '🗄️ SQLite Database Browser';
            if (dbSubtitleEl) dbSubtitleEl.textContent = 'Local Windows Desktop Database (SQLite: invoice_learning.db)';
            if (statusTextEl) statusTextEl.textContent = 'SQLite Local DB Active';
        }

        currentSelectedDbTable = data.selected_table;
        currentDbRawRows = data.rows || [];
        currentDbColumns = data.columns || [];

        if (tableNameEl) tableNameEl.textContent = currentSelectedDbTable;
        if (rowCountEl) rowCountEl.textContent = data.total_rows;

        // Render Table Selection Pills
        if (pillsContainer && data.tables) {
            pillsContainer.innerHTML = data.tables.map(t => `
                <button type="button" class="db-table-pill ${t.name === currentSelectedDbTable ? 'active' : ''}" data-table="${escapeHtml(t.name)}">
                    <span>${escapeHtml(t.name)}</span>
                    <span class="pill-badge">${t.count}</span>
                </button>
            `).join('');

            pillsContainer.querySelectorAll('.db-table-pill').forEach(btn => {
                btn.addEventListener('click', function() {
                    const tbl = this.dataset.table;
                    if (tbl) loadDatabaseBrowser(tbl);
                });
            });

            const badgeTotalEl = document.getElementById('badgeDbTables');
            if (badgeTotalEl) badgeTotalEl.textContent = data.tables.length;
        }

        renderRawTableRows(currentDbColumns, currentDbRawRows);

    } catch (err) {
        console.error('[API ERROR] GET /api/admin/raw-database:', err);
        if (tbody) {
            tbody.innerHTML = `<tr><td colspan="15" class="error-state" style="color:#ef4444; padding:24px; text-align:center;">Failed to load database: ${escapeHtml(err.message)}</td></tr>`;
        }
    }
}

function renderRawTableRows(columns, rows) {
    const thead = document.getElementById('dbTableHead');
    const tbody = document.getElementById('dbTableBody');
    const rowCountEl = document.getElementById('dbActiveRowCount');
    if (!thead || !tbody) return;

    if (!columns || columns.length === 0) {
        thead.innerHTML = '<tr><th>No Columns</th></tr>';
        tbody.innerHTML = '<tr><td class="empty-state" style="padding:20px; text-align:center; color:#94a3b8;">Empty table</td></tr>';
        return;
    }

    thead.innerHTML = '<tr>' + columns.map(c => `<th>${escapeHtml(c)}</th>`).join('') + '</tr>';

    if (!rows || rows.length === 0) {
        tbody.innerHTML = `<tr><td colspan="${columns.length}" class="empty-state" style="text-align:center; padding:30px; color:#94a3b8;">No records found in this table</td></tr>`;
        if (rowCountEl) rowCountEl.textContent = '0';
        return;
    }

    if (rowCountEl) rowCountEl.textContent = rows.length;

    tbody.innerHTML = rows.map(r => {
        const cells = columns.map(c => {
            const val = r[c];
            let displayVal = val === null || val === undefined ? '<em style="color:#64748b;">NULL</em>' : escapeHtml(String(val));
            return `<td>${displayVal}</td>`;
        }).join('');
        return `<tr>${cells}</tr>`;
    }).join('');
}

// Wire up Database Browser filter and refresh
document.addEventListener('DOMContentLoaded', function() {
    const dbSearchInput = document.getElementById('dbSearchInput');
    if (dbSearchInput) {
        dbSearchInput.addEventListener('input', function() {
            const q = this.value.trim().toLowerCase();
            if (!q) {
                renderRawTableRows(currentDbColumns, currentDbRawRows);
                return;
            }
            const filtered = currentDbRawRows.filter(r => {
                return Object.values(r).some(v => String(v || '').toLowerCase().includes(q));
            });
            renderRawTableRows(currentDbColumns, filtered);
        });
    }

    const btnRefreshDb = document.getElementById('btnRefreshDbView');
    if (btnRefreshDb) {
        btnRefreshDb.addEventListener('click', () => {
            loadDatabaseBrowser(currentSelectedDbTable);
        });
    }
});