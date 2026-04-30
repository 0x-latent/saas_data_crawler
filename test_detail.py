"""测试详情页抓取：打开5个UP主页面，拦截API响应，打印结果"""
import asyncio
import json
from playwright.async_api import async_playwright

CDP_URL = "http://localhost:9222"

TEST_URLS = [
    ("54911793", "https://huahuo.bilibili.com/#/upper/page/54911793?referer=UpperContent"),
    ("5970160", "https://huahuo.bilibili.com/#/upper/page/5970160?referer=UpperContent"),
    ("5294454", "https://huahuo.bilibili.com/#/upper/page/5294454?referer=UpperContent"),
    ("3632303408417140", "https://huahuo.bilibili.com/#/upper/page/3632303408417140?referer=UpperContent"),
    ("3546875066059052", "https://huahuo.bilibili.com/#/upper/page/3546875066059052?referer=UpperContent"),
]

INTERCEPT_APIS = {
    "/advertiser/portrait": "portrait",
    "/portrait/draft/trend_extra": "draft_trend",
    "/attention_user/trend_extra": "fans_trend",
    "/representative/list": "representative",
}


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(CDP_URL)
        context = browser.contexts[0]
        page = await context.new_page()

        for page_id, url in TEST_URLS:
            print(f"\n{'='*60}")
            print(f"测试: {url}")
            print(f"{'='*60}")

            captured = {}
            all_responses = []

            async def handle_response(response):
                resp_url = response.url
                # 记录所有API响应
                if "commercialorder" in resp_url or "huahuo" in resp_url:
                    try:
                        body = await response.json()
                        code = body.get("code", "?")
                        msg = body.get("msg", "")
                        status = body.get("status", "")
                        # 提取API路径
                        path = resp_url.split("/api/web_api/v1")[-1].split("?")[0] if "/api/web_api/v1" in resp_url else resp_url.split("?")[0][-60:]
                        all_responses.append({
                            "path": path,
                            "code": code,
                            "msg": msg,
                            "status": status,
                            "has_data": isinstance(body.get("result"), dict) and len(body.get("result", {})) > 5,
                        })

                        for api_path, key in INTERCEPT_APIS.items():
                            if api_path in resp_url:
                                if "trend_type=" in resp_url:
                                    t = resp_url.split("trend_type=")[1].split("&")[0]
                                    full_key = f"{key}_type{t}"
                                elif "query_type=" in resp_url:
                                    t = resp_url.split("query_type=")[1].split("&")[0]
                                    full_key = f"{key}_query{t}"
                                elif "type=" in resp_url and "representative" in resp_url:
                                    t = resp_url.split("type=")[1].split("&")[0]
                                    full_key = f"{key}_type{t}"
                                else:
                                    full_key = key
                                captured[full_key] = {
                                    "code": code,
                                    "msg": msg,
                                    "has_result": body.get("result") is not None,
                                    "result_type": type(body.get("result")).__name__,
                                }
                                if body.get("code") == 0 and isinstance(body.get("result"), dict):
                                    r = body["result"]
                                    captured[full_key]["nickname"] = r.get("nickname", "")
                                    captured[full_key]["upper_mid"] = r.get("upper_mid", "")
                                    captured[full_key]["fans_num"] = r.get("fans_num", "")
                    except Exception:
                        pass

            page.on("response", handle_response)

            try:
                # 先跳空白页，强制SPA完整重新加载
                await page.goto("about:blank", wait_until="load", timeout=5000)
                await asyncio.sleep(0.5)
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await asyncio.sleep(3)
            except Exception as e:
                print(f"  页面加载异常: {e}")

            # 检查页面内容
            try:
                title = await page.title()
                print(f"\n页面标题: {title}")

                # 检查是否有"未开通"提示
                body_text = await page.evaluate("() => document.body.innerText.substring(0, 500)")
                if "未开通" in body_text or "没有开通" in body_text or "暂无" in body_text:
                    print(f"页面提示: {body_text[:200]}")
            except Exception:
                pass

            # 打印所有拦截到的API
            print(f"\n拦截到的API请求 ({len(all_responses)}个):")
            for r in all_responses:
                marker = "OK" if r["code"] == 0 else f"ERR({r['code']})"
                print(f"  [{marker}] {r['path']}  msg={r['msg']}")

            print(f"\n匹配到的关键API ({len(captured)}个):")
            for key, info in captured.items():
                print(f"  {key}: code={info['code']}, msg={info['msg']}, "
                      f"result_type={info['result_type']}")
                if info.get("nickname"):
                    print(f"    -> {info['nickname']} (mid={info.get('upper_mid')}, fans={info.get('fans_num')})")

            if not captured:
                print("  (无匹配API)")

            page.remove_listener("response", handle_response)

        await page.close()
        print(f"\n{'='*60}")
        print("测试完成")


if __name__ == "__main__":
    asyncio.run(main())
