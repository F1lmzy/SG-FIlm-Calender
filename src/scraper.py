"""Scraper for Filmhouse.sg film screenings."""

from datetime import date, datetime, timedelta
import re
from typing import Dict, List, Optional

from scrapling.fetchers import Fetcher


class FilmhouseScraper:
    """Scrape film screening data from Filmhouse.sg."""

    URL = "https://filmhouse.sg/films/"

    def __init__(self, reference_date: Optional[datetime] = None) -> None:
        self.reference_date = reference_date or datetime.now()

    def scrape(self) -> List[Dict]:
        """Fetch and parse all film screenings."""
        page = Fetcher.get(self.URL)
        films: List[Dict] = []

        for film_el in page.css(".jacro-event.movie-tabs"):
            film = self._parse_film(film_el)
            if film and film["screenings"]:
                films.append(film)

        return films

    def _parse_film(self, film_el) -> Optional[Dict]:
        """Parse a single film element."""
        title = film_el.css(".liveeventtitle::text").get()
        if not title:
            return None

        film_url = film_el.css(".liveeventtitle::attr(href)").get() or ""
        duration_mins = self._extract_duration(film_el)
        year, rating, genre = self._extract_metadata(film_el)
        director, cast = self._extract_credits(film_el)
        screenings = self._parse_screenings(film_el, duration_mins)

        return {
            "title": title.strip(),
            "url": film_url,
            "year": year,
            "duration_mins": duration_mins,
            "rating": rating,
            "genre": genre,
            "director": director,
            "cast": cast,
            "screenings": screenings,
        }

    def _extract_duration(self, film_el) -> int:
        """Extract film duration in minutes."""
        for span in film_el.css(".running-time span::text").getall():
            match = re.search(r"(\d+)\s*mins", span, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return 120

    def _extract_metadata(self, film_el) -> tuple:
        """Extract year, rating, and genre."""
        year = rating = genre = ""
        for text in film_el.css(".running-time span::text").getall():
            text = text.strip()
            if text.isdigit() and len(text) == 4:
                year = text
            elif text.startswith("(") and text.endswith(")"):
                rating = text
            elif "mins" not in text.lower() and text:
                genre = text
        return year, rating, genre

    def _extract_credits(self, film_el) -> tuple:
        """Extract director and cast."""
        director = cast = ""
        for text in film_el.css(".film-info span::text").getall():
            text = text.strip()
            if text.startswith("Directed by"):
                director = text.replace("Directed by", "").strip()
            elif text.startswith("Starring"):
                cast = text.replace("Starring", "").strip()
        return director, cast

    def _parse_screenings(self, film_el, duration_mins: int) -> List[Dict]:
        """Parse all screenings for a film."""
        screenings: List[Dict] = []
        perf_lists = film_el.css(".performance-list-items")

        if not perf_lists:
            return screenings

        perf_list = perf_lists[0]
        current_date: Optional[date] = None

        # Use XPath for direct children (cssselect doesn't support '> selector')
        children = perf_list.xpath(
            './div[contains(@class, "heading")] | ./li')

        for child in children:
            classes = child.attrib.get("class", "").split()

            if "heading" in classes:
                heading_text = child.css("::text").get() or ""
                current_date = self._parse_date_heading(heading_text)
                continue

            if current_date is None:
                continue

            time_text = child.css(".film_book_button .time::text").get()
            if not time_text:
                continue

            book_url = child.css(".film_book_button::attr(href)").get() or ""

            try:
                time_obj = datetime.strptime(time_text.strip(), "%I:%M %p").time()
                start_dt = datetime.combine(current_date, time_obj)
                end_dt = start_dt + timedelta(minutes=duration_mins)

                screenings.append(
                    {
                        "start": start_dt,
                        "end": end_dt,
                        "booking_url": book_url,
                        "time_str": time_text.strip(),
                    }
                )
            except ValueError:
                continue

        return screenings

    def _parse_date_heading(self, heading_text: str) -> Optional[date]:
        """Parse date heading like 'Thursday 14th May' into a date."""
        cleaned = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", heading_text)

        for year_offset in [0, 1, -1]:
            year = self.reference_date.year + year_offset
            try:
                parsed = datetime.strptime(f"{cleaned} {year}", "%A %d %B %Y")
                result_date = parsed.date()
                days_diff = (result_date - self.reference_date.date()).days
                if -30 <= days_diff <= 365:
                    return result_date
            except ValueError:
                continue

        return None
