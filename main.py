from datetime import datetime
from re import search as re_search

from bs4 import BeautifulSoup
from pandas import DataFrame
from requests import get
from time import sleep


def parse_one_page(url, page_num):
    url += f"page-{page_num}"

    response = get(url)
    if response.status_code >= 400:
        raise Exception(f"Request error {response.status_code}: {response.content}")

    soup = BeautifulSoup(response.content, 'html.parser')
    cards = soup.find_all(class_='PropertyPriceChangeCard')

    card_dicts = []
    for card in cards:

        # get prices from the card:
        prices = [
            p.text.replace('€', '').replace(',', '')
            for p in card.find_all('span')
            if '€' in p.text
        ]
        assert len(prices) == 3
        try:
            prices = [int(p) for p in prices]
        except ValueError as e:
            raise Exception(f"Parsing error: {e}")
        assert prices[2] - prices[1] == prices[0]

        # get building name:
        name = card.find_all(class_='PropertyPriceChangeCard__Address')
        assert len(name) == 1
        name = name[0]

        # get date of price change:
        date = card.find_all(class_='PriceRegisterListItem__Date')
        assert len(date) == 1
        date = date[0]

        # save the result:
        card_dicts.append({
            'name': name.text.strip(),
            'date': date.text.strip(),
            'old_price': prices[1],
            'new_price': prices[2],
            'url': 'https://myhome.ie' + name.attrs['href'],
            'parsing_timestamp': datetime.today(),
        })

    # when we're on the first page, get total number of pages for given search parameters:
    last_page_num = None
    if page_num == 1:
        if cards:
            pages = soup.find_all('ul', class_='ngx-pagination')
            assert len(pages) == 1
            pages = pages[0].find_all('li', class_='ng-star-inserted')
            assert pages
            for page in pages:
                if page.find(class_='disabled'):
                    continue
                current_page_num = re_search(r'\d+', page.text)
                if current_page_num:
                    last_page_num = int(current_page_num[0])
        else:
            last_page_num = 1

    return card_dicts, last_page_num


def main(area=None, subarea=None):
    page = 1
    last_page = 10
    card_dicts = []

    while page <= last_page:
        url = 'https://myhome.ie/pricechanges/'
        if area:
            url += area + '/'
            if subarea:
                url += subarea + '/'
        page_card_dicts, last_page_num = parse_one_page(url, page)
        card_dicts += page_card_dicts
        if last_page_num is not None:
            last_page = last_page_num

        sleep(2)
        page += 1

    return DataFrame.from_records(card_dicts)


if __name__ == '__main__':
    AREA = 'cork-west'
    SUBAREA = 'union-hall'

    df = main(AREA, SUBAREA)
