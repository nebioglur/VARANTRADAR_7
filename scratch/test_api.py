import sys

try:
    from server import app
    print("App imported")
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['logged_in'] = True
        res = client.get('/api/dashboard_init')
        print("Status code:", res.status_code)
        print("Response:", res.data[:100])
except Exception as e:
    import traceback
    traceback.print_exc()
