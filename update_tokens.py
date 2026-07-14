import os
import json
import asyncio
import aiohttp

UIDPASS_FILE = "uidpass.json"
TOKEN_FILE = "tokens.json"
API_URL = "https://jwttoken-ten.vercel.app/token"

# একসাথে সর্বোচ্চ কয়টি রিকোয়েস্ট যাবে (৮৫০০ অ্যাকাউন্টের জন্য ৫০টি করে ব্যাচ বেস্ট)
MAX_CONCURRENT_REQUESTS = 50

def read_uidpass():
    with open(UIDPASS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

async def fetch_token_async(session, semaphore, uid, password):
    async with semaphore:
        url = f"{API_URL}?uid={uid}&password={password}"
        try:
            async with session.get(url, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    token = data.get("token")
                    if token:
                        return {"token": token}
        except Exception as e:
            print(f"Error fetching token for UID {uid}: {e}")
        return None

def update_token_file(token_list):
    folder = os.path.dirname(TOKEN_FILE)
    if folder and not os.path.exists(folder):
        os.makedirs(folder)
        
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump(token_list, f, ensure_ascii=False, indent=4)

async def main_async():
    uidpass_list = read_uidpass()
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    
    # একসাথে অনেকগুলো কানেকশন হ্যান্ডেল করার জন্য
    connector = aiohttp.TCPConnector(limit=0, ttl_dns_cache=300)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [
            fetch_token_async(session, semaphore, item["uid"], item["password"])
            for item in uidpass_list
        ]
        
        print(f"⏳ Total {len(uidpass_list)} অ্যাকাউন্টের টোকেন সংগ্রহ শুরু হচ্ছে...")
        results = await asyncio.gather(*tasks)
        
        # None ভ্যালুগুলো বাদ দিয়ে শুধু সফল টোকেন ফিল্টার করা
        new_tokens = [res for res in results if res is not None]
        
    if new_tokens:
        update_token_file(new_tokens)
        print(f"✅ {TOKEN_FILE} সফলভাবে আপডেট হয়েছে। মোট টোকেন: {len(new_tokens)}")
    else:
        print("❌ কোনো টোকেন আপডেট করা সম্ভব হয়নি।")

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
