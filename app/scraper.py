# app/scraper.py
import os
import re
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import asyncio

class WebsiteScraper:
    """Extracts structured data from client websites"""
    
    def __init__(self):
        self.timeout = 30000
    
    async def analyze_website(self, url: str) -> Dict[str, Any]:
        """Main entry point for website analysis"""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                await page.goto(url, timeout=self.timeout, wait_until="networkidle")
                
                data = {
                    "url": url,
                    "title": await self._get_title(page),
                    "meta_description": await self._get_meta_description(page),
                    "headings": await self._get_headings(page),
                    "paragraphs": await self._get_paragraphs(page),
                    "products": await self._get_products(page),
                    "services": await self._get_services(page),
                    "testimonials": await self._get_testimonials(page),
                    "about_text": await self._get_about_text(page),
                    "contact_info": await self._get_contact_info(page),
                    "social_links": await self._get_social_links(page),
                    "keywords": await self._extract_keywords(page),
                }
                
                await browser.close()
                return data
                
        except PlaywrightTimeoutError:
            return {"error": "Website timeout - check URL or connectivity"}
        except Exception as e:
            return {"error": f"Scraping failed: {str(e)}"}
    
    async def _get_title(self, page) -> str:
        try:
            return await page.title()
        except:
            return ""
    
    async def _get_meta_description(self, page) -> str:
        try:
            description = await page.evaluate('''
                () => {
                    const meta = document.querySelector('meta[name="description"]');
                    return meta ? meta.getAttribute('content') : '';
                }
            ''')
            return description or ""
        except:
            return ""
    
    async def _get_headings(self, page) -> List[str]:
        try:
            headings = await page.evaluate('''
                () => {
                    return [...document.querySelectorAll('h1, h2, h3')]
                        .map(h => h.textContent.trim())
                        .filter(text => text.length > 0);
                }
            ''')
            return headings[:20]
        except:
            return []
    
    async def _get_paragraphs(self, page) -> List[str]:
        try:
            paragraphs = await page.evaluate('''
                () => {
                    return [...document.querySelectorAll('p')]
                        .map(p => p.textContent.trim())
                        .filter(text => text.length > 30)
                        .slice(0, 10);
                }
            ''')
            return paragraphs
        except:
            return []
    
    async def _get_products(self, page) -> List[Dict]:
        try:
            products = await page.evaluate('''
                () => {
                    const selectors = ['.product', '.item', '.card', '.product-item', '[data-product]', '.product-card'];
                    const results = [];
                    selectors.forEach(selector => {
                        document.querySelectorAll(selector).forEach(el => {
                            const name = el.textContent.trim();
                            const priceEl = el.querySelector('.price, .cost, .amount, [data-price]');
                            const price = priceEl ? priceEl.textContent.trim() : '';
                            if (name && name.length > 5 && name.length < 200) {
                                results.push({ name: name.substring(0, 100), price });
                            }
                        });
                    });
                    return results.slice(0, 10);
                }
            ''')
            return products
        except:
            return []
    
    async def _get_services(self, page) -> List[str]:
        try:
            services = await page.evaluate('''
                () => {
                    const selectors = ['.service', '.service-item', '.offering', '.service-card'];
                    const results = [];
                    selectors.forEach(selector => {
                        document.querySelectorAll(selector).forEach(el => {
                            const text = el.textContent.trim();
                            if (text && text.length > 5 && text.length < 200) {
                                results.push(text.substring(0, 100));
                            }
                        });
                    });
                    return results.slice(0, 10);
                }
            ''')
            return services
        except:
            return []
    
    async def _get_testimonials(self, page) -> List[Dict]:
        try:
            testimonials = await page.evaluate('''
                () => {
                    const selectors = ['.testimonial', '.review', '.quote', '.client-says', '.feedback'];
                    const results = [];
                    selectors.forEach(selector => {
                        document.querySelectorAll(selector).forEach(el => {
                            const text = el.textContent.trim();
                            const nameEl = el.querySelector('.name, .client, .author');
                            const name = nameEl ? nameEl.textContent.trim() : '';
                            if (text && text.length > 20 && text.length < 500) {
                                results.push({ text: text.substring(0, 300), author: name.substring(0, 50) });
                            }
                        });
                    });
                    return results.slice(0, 5);
                }
            ''')
            return testimonials
        except:
            return []
    
    async def _get_about_text(self, page) -> str:
        try:
            about = await page.evaluate('''
                () => {
                    const selectors = ['.about', '.about-us', '#about', '.company-info', '.mission', '.vision'];
                    for (const selector of selectors) {
                        const el = document.querySelector(selector);
                        if (el) return el.textContent.trim().substring(0, 1000);
                    }
                    const paragraphs = document.querySelectorAll('p');
                    for (const p of paragraphs) {
                        const text = p.textContent.toLowerCase();
                        if (text.includes('about') || text.includes('mission') || text.includes('company')) {
                            return p.textContent.trim().substring(0, 500);
                        }
                    }
                    return '';
                }
            ''')
            return about
        except:
            return ""
    
    async def _get_contact_info(self, page) -> Dict:
        try:
            contact = await page.evaluate('''
                () => {
                    const result = {};
                    const text = document.body.textContent;
                    const phoneRegex = /(\\+?\\d{1,3}[-.]?)?\\(?\\d{3}\\)?[-.]?\\d{3}[-.]?\\d{4}/g;
                    const phones = text.match(phoneRegex);
                    result.phones = phones ? phones.slice(0, 3) : [];
                    const emailRegex = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}/g;
                    const emails = text.match(emailRegex);
                    result.emails = emails ? emails.slice(0, 3) : [];
                    const addressSelectors = ['.address', '.location', '.office'];
                    let address = '';
                    for (const selector of addressSelectors) {
                        const el = document.querySelector(selector);
                        if (el) { address = el.textContent.trim(); break; }
                    }
                    result.address = address;
                    return result;
                }
            ''')
            return contact
        except:
            return {"phones": [], "emails": [], "address": ""}
    
    async def _get_social_links(self, page) -> List[Dict]:
        try:
            links = await page.evaluate('''
                () => {
                    const platforms = {
                        'facebook': 'facebook.com', 'instagram': 'instagram.com',
                        'linkedin': 'linkedin.com', 'twitter': 'twitter.com',
                        'youtube': 'youtube.com', 'tiktok': 'tiktok.com'
                    };
                    const results = [];
                    document.querySelectorAll('a[href]').forEach(link => {
                        const href = link.getAttribute('href');
                        for (const [platform, domain] of Object.entries(platforms)) {
                            if (href && href.includes(domain)) {
                                results.push({ platform, url: href });
                                break;
                            }
                        }
                    });
                    return results;
                }
            ''')
            return links
        except:
            return []
    
    async def _extract_keywords(self, page) -> List[str]:
        try:
            text = await page.text_content('body')
            words = re.findall(r'\b\w{4,}\b', text)
            from collections import Counter
            counter = Counter([w.lower() for w in words])
            stopwords = {'the', 'and', 'for', 'with', 'that', 'this', 'are', 'you', 'can', 'your', 'our', 'all', 'about', 'from', 'have', 'will'}
            keywords = [(word, count) for word, count in counter.items() 
                       if word not in stopwords and len(word) > 3]
            return [word for word, count in sorted(keywords, key=lambda x: x[1], reverse=True)[:20]]
        except:
            return []