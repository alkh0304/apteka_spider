import re
import scrapy
import time

from ..items import ScrapyAptekaItem


class AptekaspiderSpider(scrapy.Spider):
    name = "apteka_spider"
    allowed_domains = ["apteka-ot-sklada.ru"]
    start_urls = [
        "https://apteka-ot-sklada.ru/catalog/sredstva-gigieny/"
        "uhod-za-polostyu-rta/zubnye-niti_-ershiki",
        "https://apteka-ot-sklada.ru/catalog/medikamenty-i-bady/"
        "antistressovoe-deystvie/uspokoitelnye",
        "https://apteka-ot-sklada.ru/catalog/medikamenty-i-bady/"
        "antistressovoe-deystvie/antidepressanty"
    ]

    def start_requests(self):
        # Указываем город Томск для первого запроса
        cookies = {
            'city': '92'
        }
        for url in self.start_urls:
            yield scrapy.Request(url=url, cookies=cookies, callback=self.parse)

    def parse(self, response):
        """Сбор данных с карточек товаров"""
        next_page_block = response.css(
            'li.ui-pagination__item.ui-pagination__item_next'
        )
        next_page = next_page_block.css('a::attr(href)').get()
        base_url = 'https://apteka-ot-sklada.ru/'
        # Если есть ссылка на следующую страницу - грузит следующую страницу.
        if next_page is not None:
            # Указываем город Томск для последующих запросов.
            cookies = {
                'city': '92'
            }
            url = base_url + next_page
            yield response.follow(url, cookies=cookies, callback=self.parse)

        for item_card in response.css('div[itemprop*=itemListElement]'):
            item = ScrapyAptekaItem()
            # Текущее время в формате timestamp.
            item['timestamp'] = int(time.time())
            # Уникальный код товара - последние цифры в ссылке на товар.
            item_url = item_card.css('a.goods-card__link::attr(href)').get()
            re_numbers = re.search(r'(\d+)_?$', item_url)
            if re_numbers:
                unique_number = re_numbers.group(1)
            item['RPC'] = unique_number
            # Ссылка на страницу товара.
            item['url'] = base_url + item_url
            # Название товара.
            item['title'] = item_card.css('span[itemprop*=name]::text').get()
            # Список тэгов.
            tags = item_card.css('li.goods-tags__item')
            tags_list_old = tags.css('span::text').getall()
            tags_list = [s.strip() for s in tags_list_old]
            item['marketing_tags'] = tags_list
            # Производитель.
            item['brand'] = item_card.css(
                'span[itemtype*=legalName]::text').get()
            # Иерархия категорий.
            category_list = response.css('ul.ui-breadcrumbs__list')
            item['section'] = category_list.css(
                'span[itemprop*=name]::text'
            ).getall()

            price_data = {}
            stock = {}
            # Выделяем зону с ценой
            price_area = item_card.css('div.goods-card__cost-area.text')
            prices = price_area.css('span::text').getall()

            # Если есть ценник, значит товар в наличии, иначе - нет.
            if price_area:
                # Поскольку товар есть, указываем это.
                stock['in_stock'] = True
                # Если цены две, значит есть скидка и её нужно вычислять.
                if len(prices) == 2:
                    price_data['current'] = float(
                        prices[0].replace('₽', '').replace(
                            ' ', '').replace('\n', ''))
                    price_data['original'] = float(
                        prices[1].replace('₽', '').replace(
                            ' ', '').replace('\n', ''))
                    discount = round(
                        (price_data['current'] / price_data['original']) * 100)
                    price_data['sale_tag'] = f'Скидка {discount}%'
                # Иначе скидки нет, а значит и вычислять её нет необходимости.
                else:
                    price_data['current'] = float(
                        prices[0].replace('₽', '').replace(
                            ' ', '').replace('\n', ''))
                    price_data['original'] = price_data['current']
                    price_data['sale_tag'] = ''
            else:
                # Если товара нет, то на сайте нет и информации о цене.
                price_data['current'] = 0.0
                price_data['original'] = 0.0
                price_data['sale_tag'] = ''
                stock['in_stock'] = False
            # На сайте нет информации об объеме товара в наличии.
            stock['count'] = 0
            item['price_data'] = price_data
            item['stock'] = stock
            # Url, на котором хранятся картинки.
            img_storage_url = "https://apteka-ot-sklada.ru/images/goods/"
            assets = {}
            # Url адрес основной картинки.
            assets['main_image'] = (img_storage_url + item['RPC'] + ".jpg")
            # Все возможные данные из карточки товара получены.
            # Оставшиеся данные собираются со страницы товара.
            yield scrapy.Request(
                item['url'],
                callback=self.parse_item,
                meta={
                    'item': item,
                    'assets': assets,
                    'img_storage_url': img_storage_url
                }
            )

    def parse_item(self, response):
        """Сбор данных со страницы товара"""
        # Подгружаем данные, собранные при парсинге карточки товара.
        item = response.meta['item']
        assets = response.meta['assets']
        img_storage_url = response.meta['img_storage_url']
        assets['set_images'] = []
        # Вытаскиваем ссылку на картинку для каждой картинки товара.
        for image_block in response.css('ul.goods-gallery__preview-list'):
            src = image_block.css('img::attr(src)').get()
            img_link = img_storage_url + src
            assets['set_images'] += [img_link]
        # 360 обзора товара и видео на сайте не нашел.
        # Добавил для общей структуры словаря
        assets['view360'] = []
        assets['video'] = []
        item['assets'] = assets
        metadata = {}
        # Вытаскиваем весь описательный текст из страницы товара.
        description_block = response.css('div[itemprop*=description]')
        desc_list = description_block.css('p::text').getall()
        description_full = ''
        for x in desc_list:
            description_full += ' ' + x
        metadata['description'] = description_full
        # Добавляем страну производителя.
        metadata['СТРАНА ПРОИЗВОДИТЕЛЬ'] = response.css(
            'span[itemtype*=location]::text'
        ).get()
        # Явного артикула на сайте нет, только код в конце ссылки.
        # По этому коду можно найти в поиске сайта любой товар.
        metadata['АРТИКУЛ'] = item['RPC']
        item['metadata'] = metadata
        item['variants'] = 1
        yield item
