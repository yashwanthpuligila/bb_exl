import urllib.request

for path in ['/', '/script.js', '/styles.css']:
    url = f'http://127.0.0.1:5000{path}'
    with urllib.request.urlopen(url) as resp:
        content = resp.read().decode('utf-8', errors='ignore')
        print(f'{path}: status {resp.status}, length {len(content)}')
        if path == '/':
            assert 'id="editInvoiceModal"' in content, "Missing editInvoiceModal"
            assert 'id="btnAddEditProductRow"' in content, "Missing btnAddEditProductRow"
            assert 'id="editModalInvoiceNumBadge"' in content, "Missing editModalInvoiceNumBadge"
            print('  -> index.html has all edit modal DOM elements')
        elif path == '/script.js':
            assert 'openEditInvoiceModal' in content, "Missing openEditInvoiceModal"
            assert 'executeSaveInvoiceEdit' in content, "Missing executeSaveInvoiceEdit"
            assert 'calculateEditTotals' in content, "Missing calculateEditTotals"
            print('  -> script.js has all edit invoice functions and handlers')
        elif path == '/styles.css':
            assert '.edit-invoice-modal-dialog' in content, "Missing .edit-invoice-modal-dialog"
            assert '.edit-products-table' in content, "Missing .edit-products-table"
            assert '.edit-totals-bar' in content, "Missing .edit-totals-bar"
            print('  -> styles.css has all edit modal styling rules')

print('\n🎉 ALL STATIC ASSETS VALIDATED OVER HTTP 200!')
