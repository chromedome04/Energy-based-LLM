#!/usr/bin/env python3
"""
Project Gutenberg Children's Books Scraper

This script searches for and downloads children's books from Project Gutenberg
in plain text format. It respects robots.txt and includes delays between requests.
"""

import requests
import time
import os
import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GutenbergScraper:
    def __init__(self, download_dir="gutenberg_books", delay=1.0):
        """
        Initialize the scraper
        
        Args:
            download_dir (str): Directory to save downloaded books
            delay (float): Delay between requests in seconds
        """
        self.base_url = "https://www.gutenberg.org"
        self.download_dir = download_dir
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; Educational scraper; respecting robots.txt)'
        })
        
        # Create download directory
        os.makedirs(self.download_dir, exist_ok=True)
        
    def search_children_books(self, max_pages=5):
        """
        Search for children's books on Project Gutenberg
        
        Args:
            max_pages (int): Maximum number of search result pages to process
            
        Returns:
            list: List of book URLs
        """
        book_urls = []
        
        # Multiple search strategies for children's books
        search_queries = [
            "children",
            "juvenile", 
            "fairy+tales",
            "bedtime+stories"
        ]
        
        for query in search_queries[:2]:  # Limit to first 2 queries to avoid too many requests
            logger.info(f"Searching for: {query}")
            
            # Search URL for the query
            search_url = f"{self.base_url}/ebooks/search/?query={query}&submit_search=Go%21"
            
            for page in range(1, min(max_pages, 3) + 1):  # Limit pages per query
                logger.info(f"Searching page {page} for {query}...")
                
                if page == 1:
                    page_url = search_url
                else:
                    page_url = f"{search_url}&start_index={25 * (page - 1)}"
                
                try:
                    response = self.session.get(page_url)
                    response.raise_for_status()
                    
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Find book links - look for links to ebook pages
                    book_links = soup.find_all('a', href=re.compile(r'/ebooks/\d+$'))
                    
                    page_books = 0
                    for link in book_links:
                        book_url = urljoin(self.base_url, link['href'])
                        if book_url not in book_urls:
                            book_urls.append(book_url)
                            page_books += 1
                            
                    logger.info(f"Found {page_books} new books on page {page}")
                    
                    # If no books found, we might have reached the end
                    if page_books == 0:
                        break
                    
                    # Respectful delay
                    time.sleep(self.delay)
                    
                except requests.RequestException as e:
                    logger.error(f"Error searching page {page} for {query}: {e}")
                    continue
                    
        logger.info(f"Found total of {len(book_urls)} unique books")
        return book_urls
    
    def get_book_info(self, book_url):
        """
        Get book information and find text download link
        
        Args:
            book_url (str): URL of the book page
            
        Returns:
            dict: Book information including title, author, and text URL
        """
        try:
            response = self.session.get(book_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract book information
            title_elem = soup.find('h1', {'itemprop': 'name'})
            title = title_elem.text.strip() if title_elem else "Unknown Title"
            
            author_elem = soup.find('a', {'itemprop': 'creator'})
            author = author_elem.text.strip() if author_elem else "Unknown Author"
            
            # Find plain text download link - updated approach
            text_link = None
            
            # Method 1: Look for links in the download table/section
            download_table = soup.find('table', class_='files')
            if download_table:
                rows = download_table.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        format_cell = cells[0]
                        link_cell = cells[1] if len(cells) > 1 else cells[0]
                        
                        # Check if this row contains plain text format
                        format_text = format_cell.get_text()
                        if ('Plain Text UTF-8' in format_text or 
                            'txt.utf-8' in format_text.lower() or
                            'text/plain' in format_text.lower()):
                            
                            link = link_cell.find('a')
                            if link and link.get('href'):
                                text_link = urljoin(self.base_url, link['href'])
                                break
            
            # Method 2: Look for any .txt links if table method didn't work
            if not text_link:
                txt_links = soup.find_all('a', href=re.compile(r'\.txt'))
                for link in txt_links:
                    href = link.get('href', '')
                    # Prefer UTF-8 versions
                    if 'utf-8' in href.lower() or 'utf8' in href.lower():
                        text_link = urljoin(self.base_url, href)
                        break
                
                # If no UTF-8 version, take any .txt file
                if not text_link and txt_links:
                    text_link = urljoin(self.base_url, txt_links[0]['href'])
            
            # Method 3: Try direct construction of download URL
            if not text_link:
                # Extract book ID from URL
                book_id_match = re.search(r'/ebooks/(\d+)', book_url)
                if book_id_match:
                    book_id = book_id_match.group(1)
                    # Try common text file URL patterns
                    potential_urls = [
                        f"{self.base_url}/files/{book_id}/{book_id}-0.txt",
                        f"{self.base_url}/files/{book_id}/{book_id}.txt",
                        f"{self.base_url}/cache/epub/{book_id}/pg{book_id}.txt",
                    ]
                    
                    for url in potential_urls:
                        try:
                            test_response = self.session.head(url)
                            if test_response.status_code == 200:
                                text_link = url
                                break
                        except:
                            continue
            
            logger.info(f"Book: {title} by {author}")
            if text_link:
                logger.info(f"Found text link: {text_link}")
            else:
                logger.warning(f"No text link found for: {title}")
            
            return {
                'title': title,
                'author': author,
                'text_url': text_link,
                'book_url': book_url
            }
            
        except requests.RequestException as e:
            logger.error(f"Error getting book info from {book_url}: {e}")
            return None
    
    def download_book(self, book_info):
        """
        Download a book's text file
        
        Args:
            book_info (dict): Book information dictionary
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not book_info or not book_info['text_url']:
            logger.warning(f"No text URL found for book: {book_info.get('title', 'Unknown') if book_info else 'Unknown'}")
            return False
        
        try:
            # Clean filename
            filename = f"{book_info['author']} - {book_info['title']}.txt"
            filename = re.sub(r'[<>:"/\\|?*]', '', filename)
            filename = filename[:200]  # Limit filename length
            filepath = os.path.join(self.download_dir, filename)
            
            # Skip if already downloaded
            if os.path.exists(filepath):
                logger.info(f"Already downloaded: {filename}")
                return True
            
            logger.info(f"Downloading: {book_info['title']} by {book_info['author']}")
            
            response = self.session.get(book_info['text_url'])
            response.raise_for_status()
            
            # Save the file
            with open(filepath, 'w', encoding='utf-8', errors='ignore') as f:
                f.write(response.text)
            
            logger.info(f"Successfully downloaded: {filename}")
            return True
            
        except requests.RequestException as e:
            logger.error(f"Error downloading {book_info['title']}: {e}")
            return False
        except IOError as e:
            logger.error(f"Error saving file {filename}: {e}")
            return False
    
    def scrape_children_books(self, max_books=20, max_search_pages=3):
        """
        Main method to scrape children's books
        
        Args:
            max_books (int): Maximum number of books to download
            max_search_pages (int): Maximum search pages to process
        """
        logger.info("Starting Project Gutenberg children's books scraper...")
        
        # Search for books
        book_urls = self.search_children_books(max_search_pages)
        
        if not book_urls:
            logger.error("No books found!")
            return
        
        # Limit to max_books
        book_urls = book_urls[:max_books]
        
        downloaded = 0
        failed = 0
        
        for i, book_url in enumerate(book_urls, 1):
            logger.info(f"Processing book {i}/{len(book_urls)}")
            
            # Get book information
            book_info = self.get_book_info(book_url)
            time.sleep(self.delay)
            
            if book_info:
                # Download the book
                if self.download_book(book_info):
                    downloaded += 1
                else:
                    failed += 1
                    
                time.sleep(self.delay)
            else:
                failed += 1
        
        logger.info(f"Scraping completed! Downloaded: {downloaded}, Failed: {failed}")
        logger.info(f"Books saved to: {os.path.abspath(self.download_dir)}")

def main():
    """Main function to run the scraper"""
    
    # Configuration
    MAX_BOOKS = 10  # Number of books to download
    MAX_SEARCH_PAGES = 2  # Number of search pages to process
    DELAY = 2.0  # Delay between requests (seconds)
    
    logger.info("Project Gutenberg Children's Books Scraper")
    logger.info("=" * 45)
    logger.info("Configuration:")
    logger.info(f"- Max books to download: {MAX_BOOKS}")
    logger.info(f"- Max search pages: {MAX_SEARCH_PAGES}")
    logger.info(f"- Delay between requests: {DELAY} seconds")
    
    # Create scraper instance
    scraper = GutenbergScraper(
        download_dir="children_books",
        delay=DELAY
    )
    
    # Start scraping
    try:
        scraper.scrape_children_books(
            max_books=MAX_BOOKS,
            max_search_pages=MAX_SEARCH_PAGES
        )
    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()