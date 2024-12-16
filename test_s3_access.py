import requests

def test_public_s3_access():
    # Test URL
    url = "https://genosonggenerator.s3.us-east-2.amazonaws.com/songs/user:1297-mureka:45311292604417-song:45361450319874/music_45361387405315_Rjcdc3AcbenXxfK4SJacpp_nrgeoo.mp3"
    
    # Test with different headers to simulate browser requests
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Origin': 'http://127.0.0.1:5000',
        'Referer': 'http://127.0.0.1:5000/'
    }
    
    try:
        # Try direct access
        print("Testing direct access...")
        response = requests.get(url)
        print(f"Direct access status: {response.status_code}")
        print(f"Direct access headers: {response.headers}")
        
        # Try with browser headers
        print("\nTesting with browser headers...")
        response_with_headers = requests.get(url, headers=headers)
        print(f"Browser access status: {response_with_headers.status_code}")
        print(f"Browser access headers: {response_with_headers.headers}")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_public_s3_access() 