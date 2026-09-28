from pathlib import Path
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

PATH = Path('avito_feed_batch_01_haier.xml')
errors = []
warnings = []

try:
    root = ET.parse(PATH).getroot()
except Exception as exc:
    print('FEED_VALIDATION_ERROR xml_parse', type(exc).__name__)
    raise SystemExit(1)

if root.tag != 'Ads':
    errors.append('root tag must be Ads')
if root.attrib.get('formatVersion') != '3':
    errors.append('formatVersion must be 3')
if root.attrib.get('target') != 'Avito.ru':
    errors.append('target must be Avito.ru')

ads = root.findall('Ad')
if len(ads) != 1:
    errors.append(f'expected exactly 1 Ad, got {len(ads)}')

required = {
    'Id','AvitoId','ListingFee','AdStatus','Address','Title','Description','Images','ContactMethod',
    'Category','Price','AdType','GoodsType','ProductType','Condition','GoodsSubType','Vendor',
    'AirConditionerType','AirConditionerSubType'
}
expected = {
    'Id':'BC-7748832830',
    'AvitoId':'7748832830',
    'ListingFee':'Package',
    'AdStatus':'Free',
    'Category':'Бытовая техника',
    'Price':'18990',
    'AdType':'Товар приобретен на продажу',
    'GoodsType':'Климатическое оборудование',
    'ProductType':'Кондиционеры и запчасти',
    'Condition':'Новое',
    'GoodsSubType':'Кондиционеры',
    'Vendor':'Haier',
    'AirConditionerType':'Сплит-система',
    'AirConditionerSubType':'Настенный',
    'ContactMethod':'По телефону и в сообщениях',
}

for ad in ads:
    tags = {child.tag for child in ad}
    missing = sorted(required - tags)
    if missing:
        errors.append('missing required tags: ' + ', '.join(missing))

    def text(tag):
        el = ad.find(tag)
        return (el.text or '').strip() if el is not None else ''

    for tag, value in expected.items():
        if text(tag) != value:
            errors.append(f'{tag} expected {value!r}, got {text(tag)!r}')

    title = text('Title')
    desc = text('Description')
    address = text('Address')
    if not title or len(title) > 50:
        errors.append(f'Title length invalid: {len(title)}')
    if '₽' in title:
        errors.append('Title must not contain price')
    if not desc or len(desc) > 7500:
        errors.append(f'Description length invalid: {len(desc)}')
    if not address:
        errors.append('Address is empty')
    try:
        price = int(text('Price'))
        if price <= 0:
            errors.append('Price must be positive')
    except ValueError:
        errors.append('Price must be integer')

    if ad.find('WholesaleType') is not None:
        warnings.append('WholesaleType present: verify all dependent wholesale fields')
    if 'Опт' in title or 'опт' in title.lower():
        warnings.append('Title mentions wholesale; verify WholesaleType dependency')

    images = ad.find('Images')
    image_nodes = images.findall('Image') if images is not None else []
    if not image_nodes:
        errors.append('At least one Image is required')
    if len(image_nodes) > 10:
        errors.append('No more than 10 images allowed')
    for i, node in enumerate(image_nodes, 1):
        url = (node.attrib.get('url') or '').strip()
        p = urlparse(url)
        if p.scheme not in {'http','https'} or not p.netloc:
            errors.append(f'Image {i} has invalid URL')

ids = [((ad.findtext('Id') or '').strip()) for ad in ads]
avito_ids = [((ad.findtext('AvitoId') or '').strip()) for ad in ads]
if len(ids) != len(set(ids)):
    errors.append('duplicate Id')
if len(avito_ids) != len(set(avito_ids)):
    errors.append('duplicate AvitoId')

print(f'FEED_VALIDATION_ADS {len(ads)}')
print(f'FEED_VALIDATION_ERRORS {len(errors)}')
for err in errors:
    print('FEED_ERROR', err)
print(f'FEED_VALIDATION_WARNINGS {len(warnings)}')
for warn in warnings:
    print('FEED_WARNING', warn)
print('FEED_READY', int(not errors))

if errors:
    raise SystemExit(1)
