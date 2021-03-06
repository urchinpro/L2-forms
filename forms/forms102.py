from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, portrait
from reportlab.lib.units import mm
from copy import deepcopy
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.graphics.barcode import code128, qr
from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import Drawing

import os.path
from io import BytesIO
from . import forms_func
from directions.models import Napravleniya, IstochnikiFinansirovaniya, Issledovaniya
from clients.models import Card, Document
from laboratory.settings import FONTS_FOLDER
import simplejson as json
from datetime import *
import datetime
import locale
import sys
import pytils
from appconf.manager import SettingManager
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.colors import white, black
import zlib


class PageNumCanvas(canvas.Canvas):
    """
    Adding a Page Number of Total
    """

    # ----------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        """Constructor"""
        canvas.Canvas.__init__(self, *args, **kwargs)
        self.pages = []

    # ----------------------------------------------------------------------
    def showPage(self):
        """
        On a page break, add information to the list
        """
        self.pages.append(dict(self.__dict__))
        self._startPage()

    # ----------------------------------------------------------------------
    def save(self):
        """
        Add the page number to each page (page x of y)
        """
        page_count = len(self.pages)

        for page in self.pages:
            self.__dict__.update(page)
            self.draw_page_number(page_count)
            canvas.Canvas.showPage(self)

        canvas.Canvas.save(self)

    # ----------------------------------------------------------------------
    def draw_page_number(self, page_count):
        """
        Add the page number
        """
        page = "Лист {} из {}".format(self._pageNumber, page_count)
        self.setFont("PTAstraSerifReg", 9)
        self.drawRightString(31 * mm, 10 * mm, page)




def form_01(request_data):
    """
    Договор, включающий услуги на оплату и необходимые реквизиты
    """
    form_name = "Договор"

    ind_card = Card.objects.get(pk=request_data["card_pk"])
    ind = ind_card.individual
    ind_doc = Document.objects.filter(individual=ind, is_active=True)
    ind_dir = json.loads(request_data["dir"])
    #exec_person = print(request_data.user.doctorprofile.fio)
    exec_person = 'Иванов Иван Иванович'

    # Получить данные с клиента физлицо-ФИО, пол, дата рождения
    individual_fio = ind.fio()
    individual_date_born = ind.bd()

    # Получить все источники, у которых title-ПЛАТНО
    ist_f = []
    ist_f = list(IstochnikiFinansirovaniya.objects.values_list('id').filter(title__exact='Платно'))
    ist_f_list = []
    ist_f_list = ([int(x[0]) for x in ist_f])


    napr = Napravleniya.objects.filter(id__in=ind_dir)
    dir_temp = []

    #Проверить, что все направления принадлежат к одной карте и имеют ист. финансирования "Платно"
    num_contract_set = set()
    for n in napr:
        if (n.istochnik_f_id in ist_f_list) and (n.client ==ind_card):
            num_contract_set.add(n.num_contract)
            dir_temp.append(n.pk)

    # получить УСЛУГИ по направлениям(отфильтрованы по "платно" и нет сохраненных исследований) в Issledovaniya
    research_direction = forms_func.get_research_by_dir(dir_temp)

    # получить по направлению-услугам цену из Issledovaniya
    research_price = forms_func.get_coast_from_issledovanie(research_direction)

    #Получить Итоговую стр-ру данных
    result_data = forms_func.get_final_data(research_price)

    today = datetime.datetime.now()
    date_now1 = datetime.datetime.strftime(today, "%y%m%d%H%M%S%f")[:-3]
    date_now_str = str(ind_card.pk) + str(date_now1)


    # Проверить записан ли номер контракта в направлениях
    # ПереЗаписать номер контракта Если в наборе направлений значение None
    num_contract_set = set()
    napr_end=[]
    napr_end = Napravleniya.objects.filter(id__in=result_data[3])
    for n in napr_end:
        num_contract_set.add(n.num_contract)

    if (len(num_contract_set) == 1) and (None in num_contract_set):
        print('Перезаписано т.к. было NONE')
        Napravleniya.objects.filter(id__in=result_data[3]).update(num_contract=date_now_str)
    # ПереЗаписать номер контракта Если в наборе направлении значение разные значения
    if len(num_contract_set) > 1:
        print('Перезаписано т.к. были разные контракты в направлениях')
        Napravleniya.objects.filter(id__in=result_data[3]).update(num_contract=date_now_str)

    if (len(num_contract_set) == 1) and (not None in num_contract_set):
        print('No-No-No-No не надо создавать номер контракта он есть')
        print()
        date_now_str = num_contract_set.pop()

   # Получить данные физлицо-документы: паспорт, полис, снилс
    document_passport = "Паспорт РФ"
    documents = forms_func.get_all_doc(ind_doc)
    document_passport_num = documents['passport']['num']
    document_passport_serial = documents['passport']['serial']
    document_passport_date_start = documents['passport']['date_start']
    document_passport_issued = documents['passport']['issued']

    if sys.platform == 'win32':
        locale.setlocale(locale.LC_ALL, 'rus_rus')
    else:
        locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')

    # Генерировать pdf-Лист на оплату
    pdfmetrics.registerFont(TTFont('PTAstraSerifBold', os.path.join(FONTS_FOLDER, 'PTAstraSerif-Bold.ttf')))
    pdfmetrics.registerFont(TTFont('PTAstraSerifReg', os.path.join(FONTS_FOLDER, 'PTAstraSerif-Regular.ttf')))
    pdfmetrics.registerFont(TTFont('Symbola', os.path.join(FONTS_FOLDER, 'Symbola.ttf')))

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            leftMargin=12 * mm,
                            rightMargin=5 * mm, topMargin=6 * mm,
                            bottomMargin=22 * mm, allowSplitting=1,
                            title="Форма {}".format("Лист на оплату"))
    width, height = portrait(A4)
    styleSheet = getSampleStyleSheet()
    style = styleSheet["Normal"]
    style.fontName = "PTAstraSerifReg"
    style.fontSize = 9
    style.leading = 12
    style.spaceAfter = 0 * mm
    style.alignment = TA_JUSTIFY
    style.firstLineIndent = 15
    styleBold = deepcopy(style)
    styleBold.fontName = "PTAstraSerifBold"
    styleCenter = deepcopy(style)
    styleCenter.alignment = TA_CENTER
    styleCenter.fontSize = 9
    styleCenter.leading = 10
    styleCenter.spaceAfter = 0 * mm
    styleCenterBold = deepcopy(styleBold)
    styleCenterBold.alignment = TA_CENTER
    styleCenterBold.fontSize = 20
    styleCenterBold.leading = 15
    styleCenterBold.face = 'PTAstraSerifBold'
    styleJustified = deepcopy(style)
    styleJustified.alignment = TA_JUSTIFY
    styleJustified.spaceAfter = 4.5 * mm
    styleJustified.fontSize = 12
    styleJustified.leading = 4.5 * mm

    objs = []
    barcode128 = code128.Code128(date_now_str, barHeight=6 * mm, barWidth=1.25)

    objs.append(Spacer(1, 11 * mm))

    # head = [
    #     Paragraph('ДОГОВОР &nbsp;&nbsp; № <u>{}</u>'.format(date_now_str),styleCenter),
    #     Spacer(1, 1 * mm),
    #     Paragraph('НА ОКАЗАНИЕ ПЛАТНЫХ МЕДИЦИНСКИХ УСЛУГ НАСЕЛЕНИЮ', styleCenter),
    #     ]
    objs.append(Paragraph('ДОГОВОР &nbsp;&nbsp; № <u>{}</u>'.format(date_now_str),styleCenter))
    objs.append(Spacer(1, 1 * mm))
    objs.append(Paragraph('НА ОКАЗАНИЕ ПЛАТНЫХ МЕДИЦИНСКИХ УСЛУГ НАСЕЛЕНИЮ', styleCenter))
    styleTCenter = deepcopy(styleCenter)
    styleTCenter.alignment = TA_CENTER
    styleTCenter.leading = 3.5 * mm

    styleTBold = deepcopy(styleCenterBold)
    styleTBold.fontSize = 10
    styleTBold.alignment = TA_LEFT

    # barcode128 = code128.Code128(date_now_str,barHeight= 4 * mm, barWidth = 1.25)

    date_now = pytils.dt.ru_strftime(u"%d %B %Y", inflected=True, date=datetime.datetime.now())

    styleTR = deepcopy(style)
    styleTR.alignment = TA_RIGHT

    opinion = [
        [Paragraph('г. Иркутск', style),
         Paragraph('{} года'.format(date_now), styleTR)],
    ]

    tbl = Table(opinion, colWidths=(95 * mm, 95 * mm))

    tbl.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1.0, colors.white),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1.5 * mm),
        ]))

    objs.append(Spacer(1, 5 * mm))
    objs.append(tbl)


    objs.append(Spacer(1, 4.5 * mm))
    hospital_name = SettingManager.get("rmis_orgname")
    hospital_short_name = SettingManager.get("org_title")
    hospital_address = SettingManager.get("org_address")

    post_contract = SettingManager.get("post_contract")
    document_base = SettingManager.get("document_base")

    if document_passport_issued:
        passport_who_give = document_passport_issued
    else:
        passport_who_give = "______________________________________________________________________"


    if ind_card.main_address:
        main_address = ind_card.main_address
    else:
        main_address = "______________________________________________________________________"

    if ind_card.fact_address:
        fact_address = ind_card.fact_address
    elif main_address:
        fact_address = main_address
    else:
        fact_address = "______________________________________________________________________"


    objs.append(Paragraph('{}, именуемая в дальнейшем "Исполнитель", в лице {} {}, действующего(ей) на основании {} с '
          'одной стороны, и <u>{}</u>, именуемый(ая) в дальнейшем "Пациент", дата рождения {} г., '
          'паспорт: {}-{} '
          'выдан {} г. '
          'кем: {} '
          'зарегистрирован по адресу: {}, '
          'адрес проживания: {} '
          'с другой стороны, вместе также именуемые "Стороны", заключили настоящий договор (далее - "Договор") о нижеследующем:'
                          .
                          format(hospital_name, post_contract,exec_person,document_base, individual_fio,individual_date_born,
                                 document_passport_serial, document_passport_num,document_passport_date_start,
                                 passport_who_give, main_address, fact_address),style))

    objs.append(Spacer(1, 2 * mm))
    objs.append(Paragraph('1. ПРЕДМЕТ ДОГОВОРА',styleCenter))
    objs.append(Paragraph('1.1. Исполнитель на основании обращения Пациента обязуется оказать ему медицинские услуги в соответствие с лицензией:', style))

    #Касьяненко начало шаблон услуг только для водителей, на работу
    template_research = "Перечень услуг"
    # Касьяненко конец

    tr = ""
    if template_research:
        tr = template_research
    objs.append(Spacer(1, 2 * mm))
    objs.append(Paragraph('{}'.format(tr), style))

    styleTB = deepcopy(style)
    styleTB.firstLineIndent =0
    styleTB.fontSize = 8.5
    styleTB.alignment = TA_CENTER
    styleTB.fontName = "PTAstraSerifBold"

    styleTC = deepcopy(style)
    styleTC.firstLineIndent = 0
    styleTC.fontSize = 8.5
    styleTC.alignment = TA_LEFT

    styleTCright = deepcopy(styleTC)
    styleTCright.alignment = TA_RIGHT

    styleTCcenter=deepcopy(styleTC)
    styleTCcenter.alignment = TA_CENTER

    opinion = []
    if result_data[2]=='no_discount':
        opinion = [
            [Paragraph('Код услуги', styleTB), Paragraph('Направление', styleTB), Paragraph('Услуга', styleTB),
             Paragraph('Цена,<br/>руб.', styleTB), Paragraph('Кол-во, усл.', styleTB),
             Paragraph('Сумма, руб.', styleTB), ],
        ]
    else:
        opinion = [
            [Paragraph('Код услуги', styleTB), Paragraph('Направление', styleTB), Paragraph('Услуга', styleTB),
             Paragraph('Цена,<br/>руб.', styleTB), Paragraph('Скидка<br/>Наценка<br/>%', styleTB),
             Paragraph('Цена со<br/> скидкой,<br/>руб.', styleTB),
             Paragraph('Кол-во, усл.', styleTB), Paragraph('Сумма, руб.', styleTB), ],
        ]

    # example_template = [
    #     ['1.2.3','4856397','Полный гематологический анализ','1000.00','0','1000.00','1','1000.00'],
    #     ['1.2.3','','РМП','2500.45','0','2500.45','1','2500.45'],
    #     ['1.2.3', '4856398', 'УЗИ брюшной полости', '3500.49', '0', '3500.49', '1', '3500.49'],
    #     ['1.2.3','4856398','Эзофагогастродуоденоскопия','5700.99','0','5700.99','1','5700.99']
    # ]
    # #

    example_template=result_data[0]

    list_g =[]

    #используется range(len()) - к определенной колонке (по номеру) применяется свое свойство
    for i in range(len(example_template)):
        list_t = []
        for j in range(len(example_template[i])):
            if j in (3,5,7):
                s=styleTCright
            elif j in (4,6):
                s=styleTCcenter
            else:
                s=styleTC
            list_t.append(Paragraph(example_template[i][j],s))
        list_g.append(list_t)

    sum_research = result_data[1]

    sum_research_decimal = sum_research.replace(' ', '')

    opinion.extend(list_g)

    if result_data[2] == 'is_discount':
        tbl = Table(opinion, colWidths=(18 * mm, 19 * mm, 52 * mm, 22 * mm, 21 * mm, 22 * mm, 13 * mm, 25 * mm))
    else:
        tbl = Table(opinion, colWidths=(23 * mm, 34 * mm, 62 * mm, 22 * mm, 23 * mm, 25 * mm))

    tbl.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1.0, colors.black),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1.5 * mm),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    objs.append(tbl)
    objs.append(Spacer(1, 1 * mm))
    objs.append(Paragraph('<font size=12> Итого: {}</font>'.format(sum_research), styleTCright))
    objs.append(Spacer(1,2 * mm))

    objs.append(Spacer(1, 3 * mm))
    objs.append(Paragraph('(далее - "медицинские услуги"), а Пациент уплачивает Исполнителю вознаграждение в размере, '
                          'порядке и сроки, которые установлены настоящим Договором.', style))
    objs.append(Paragraph('1.2.	Исполнитель оказывает услуги по месту своего нахождения по адресу: '
          'г. Иркутск, Байкальская, 201, в соответствии с установленными Правилами предоставления платных медицинских услуг.', style))
    objs.append(Spacer(1, 2 * mm))
    objs.append(Paragraph('2. ПРАВА И ОБЯЗАННОСТИ СТОРОН', styleCenter))
    objs.append(Paragraph('<u>2.1. Исполнитель обязуется:</u>',style))
    objs.append(Paragraph('2.1.1. Обеспечить Пациента бесплатной, доступной и достоверной информацией о платных медицинских услугах, '
                          'содержащей следующие сведения о:', style))
    objs.append(Paragraph('а) порядках оказания медицинской помощи и стандартах медицинской помощи, применяемых при предоставлении платных медицинских услуг;', style))
    objs.append(Paragraph('б) данных о конкретном медицинском работнике, предоставляющем соответствующую платную медицинскую услугу (его профессиональном образовании и квалификации);', style))
    objs.append(Paragraph('в) данных о методах оказания медицинской помощи, связанных с ними рисках, возможных видах медицинского вмешательства, их последствиях и ожидаемых результатах оказания медицинской помощи;', style))
    objs.append(Paragraph('г) других сведениях, относящихся к предмету настоящего Договора.', style))
    objs.append(Paragraph('2.1.2.Оказывать Пациенту услуги, предусмотренные п. 1.1 настоящего Договора, а при необходимости и дополнительные услуги.', style))
    objs.append(Paragraph('2.1.3.Давать при необходимости по просьбе Пациента разъяснения о ходе оказания услуг ему и '
                          'предоставлять по требованию Пациента необходимую медицинскую документацию.', style))
    objs.append(Paragraph('2.1.4.Предоставить в доступной форме информацию о возможности получения соответствующих видов '
                          'и объемов медицинской помощи без взимания платы в рамках Программы государственных гарантий '
                          'бесплатного оказания гражданам медицинской помощи и территориальной программы государственных гарантий '
                          'бесплатного оказания гражданам медицинской помощи.', style))
    objs.append(Paragraph('2.15. Соблюдать порядки оказания медицинской помощи, утвержденные Министерством здравоохранения '
                          'Российской Федерации.',style))
    objs.append(Paragraph('<u>2.2. Пациент обязуется:</u>',style))
    objs.append(Paragraph('2.2.1. Соблюдать назначение и рекомендации лечащих врачей.', style))
    objs.append(Paragraph('2.2.3. Оплачивать услуги Исполнителя в порядке, сроки и на условиях, которые установлены настоящим Договором.', style))
    objs.append(Paragraph('2.2.4. Подписывать своевременно акты об оказании услуг Исполнителем.', style))
    objs.append(Paragraph('2.2.5. Кроме того Пациент обязан:', style))
    objs.append(Paragraph('- информировать врача о перенесенных заболеваниях, известных ему аллергических реакциях, противопоказаниях;', style))
    objs.append(Paragraph('- соблюдать правила поведения пациентов в медицинском учреждении, режим работы медицинского учреждения;', style))
    objs.append(Paragraph('- выполнять все рекомендации медицинского персонала и третьих лиц, оказывающих ему по настоящему Договору'
            'медицинские услуги, по лечению, в том числе соблюдать указания медицинского учреждения, предписанные на период после оказания услуг.', style))
    objs.append(Paragraph('2.3.	Предоставление Исполнителем дополнительных услуг оформляется дополнительным соглашением Сторон и оплачивается дополнительно.', style))
    objs.append(Paragraph('2.4.	Стороны обязуются хранить в тайне лечебную, финансовую и иную конфиденциальную информацию, '
                          'полученную от другой Стороны при исполнении настоящего Договора.', style))
    objs.append(Paragraph('3. ПОРЯДОК ИСПОЛНЕНИЯ ДОГОВОРА', styleCenter))
    objs.append(Paragraph('3.1.	Условия получения Пациентом медицинских услуг: (вне медицинской организации; амбулаторно; '
                          'в дневном стационаре; стационарно; указать,организационные моменты, связанные с оказанием медицинских услуг)', style))
    objs.append(Paragraph('3.2.	В случае если при предоставлении платных медицинских услуг требуется предоставление '
                          'на возмездной основе дополнительных медицинских услуг, не предусмотренных настоящим Договором, '
                          'Исполнитель обязан предупредить об этом Пациента.', style))
    objs.append(Paragraph('Без согласия Пациента Исполнитель не вправе предоставлять дополнительные медицинские услуги на возмездной основе.', style))
    objs.append(Paragraph('3.3.	В случае, если при предоставлении платных медицинских услуг потребуется предоставление '
                          'дополнительных медицинских услуг по экстренным показаниям для устранения угрозы жизни Пациента'
                          ' при внезапных острых заболеваниях, состояниях, обострениях хронических заболеваний, такие '
                          'медицинские услуги оказываются без взимания платы в соответствии с Федеральным загоном '
                          'от 21.11.2011N 323-ФЗ "Об основах охраны здоровья граждан в Российской Федерации".', style))
    objs.append(Paragraph('3.4.	В случае отказа Пациента после заключения Договора от получения медицинских услуг Договор '
                          'расторгается. При этом Пациент оплачивает Исполнителю фактически понесенные Исполнителем расходы,'
                          'связанные с исполнением обязательств по Договору. ', style))
    objs.append(Paragraph('3.5. К отношениям, связанным с исполнением настоящего Договора, применяются положения Закона '
                          'Российской Федерации от 7 февраля 1992 г. N 2300-1 "О защите прав потребителей".', style))
    objs.append(Paragraph('4. ПОРЯДОК ОПЛАТЫ', styleCenter))

    s = pytils.numeral.rubles(float(sum_research_decimal))
    objs.append(Paragraph('4.1.	Стоимость медицинских услуг составляет: <u>{}</u> '.format(s.capitalize()), style))
    objs.append(Paragraph('Сроки оплаты:', style))
    objs.append(Paragraph('Предоплата________________________________________ , оставшаяся сумма______________________________ рублей', style))
    objs.append(Paragraph('Сроки оплаты: _________________________', style))
    objs.append(Paragraph('4.2.	Компенсируемые расходы Исполнителя на _________________________________________________', style))
    objs.append(Paragraph('составляют_____________________ рублей', style))
    objs.append(Paragraph('4.3.	Оплата услуг производится путем перечисления суммы на расчетный счет Исполнителя или путем внесения в кассу Исполнителя.', style))
    objs.append(Paragraph('Пациенту в соответствии с законодательством Российской Федерации выдается документ; '
                          'подтверждающий произведенную оплату предоставленных медицинских услуг (кассовый чек, квитанция '
                          'или иные документы).', style))
    objs.append(Paragraph('4.4.	Дополнительные услуги оплачиваются на основании акта об оказанных услугах, подписанного Сторонами.', style))
    objs.append(Paragraph('5. ОТВЕТСТВЕННОСТЬ СТОРОН', styleCenter))
    objs.append(Paragraph('5.1.	Исполнитель несет ответственность перед Пациентом за неисполнение или ненадлежащее '
                          'исполнение условий настоящего Договора, несоблюдение требований, предъявляемых к методам '
                          'диагностики, профилактики и лечения, разрешенным на территории Российской Федерации, а также '
                          'в случае причинения вреда здоровью и жизни Пациента.', style))
    objs.append(Paragraph('5.2.	При несоблюдении Исполнителем обязательств по срокам исполнения услуг Пациент вправе по своему выбору:', style))
    objs.append(Paragraph('- назначить новый срок оказания услуги;', style))
    objs.append(Paragraph('- потребовать уменьшения стоимости предоставленной услуги;', style))
    objs.append(Paragraph('- потребовать исполнения услуги другим специалистом;', style))
    objs.append(Paragraph('- расторгнуть настоящий Договор и потребовать возмещения убытков.', style))
    objs.append(Paragraph('5.3.	Ни одна из Сторон не будет нести ответственности за полное или частичное неисполнение другой '
                          'Стороной своих обязанностей, если, неисполнение будет являться следствием обстоятельств непреодолимой '
                          'силы, таких как, пожар, наводнение, землетрясение, забастовки и другие стихийные бедствия; '
                          'война и военные действия или другие обстоятельства, находящиеся вне контроля Сторон, '
                          'препятствующие выполнению настоящего Договора, возникшие после заключения Договора, а также по '
                          'иным основаниям, предусмотренным законом', style))
    objs.append(Paragraph('Если любое из таких обстоятельств непосредственно повлияло на неисполнение обязательства в '
                          'срок, указанный в Договоре, то этот срок соразмерно отодвигается на время действия соответствующего '
                          'обстоятельства.', style))
    objs.append(Paragraph('5.4.	Вред, причиненный жизни или здоровью Пациента в результате предоставления некачественной '
                          'платной медицинской услуги, подлежит возмещению Исполнителем в соответствии с законодательством '
                          'Российской Федерации.', style))
    objs.append(Paragraph('6. ПОРЯДОК РАССМОТРЕНИЯ СПОРОВ', styleCenter))
    objs.append(Paragraph('6.1.	Все споры, претензии и разногласия, которые могут возникнуть между Сторонами, будут '
                          'разрешаться путем переговоров.', style))
    objs.append(Paragraph('6.2.	При не урегулировании в процессе переговоров спорных вопросов споры подлежат рассмотрению '
                          'в судебном порядке.', style))
    objs.append(Paragraph('7. СРОК ДЕЙСТВИЯ ДОГОВОРА', styleCenter))
    objs.append(Paragraph('7.1.	Срок действия настоящего Договора: с «	»	201	г. по «	»	201	г.', style))
    objs.append(Paragraph('7.2.	Настоящий Договор, может быть, расторгнут по обоюдному согласию Сторон или в порядке, '
                          'предусмотренном действующим законодательством.', style))
    objs.append(Paragraph('7.3.	Все изменения и дополнения к настоящему Договору, а также его расторжение считаются '
                          'действительными при условии, если они совершены в письменной форме и подписаны уполномоченными'
                          ' на то представителями обеих Сторон.', style))
    objs.append(Paragraph('8. ИНЫЕ УСЛОВИЯ', styleCenter))
    objs.append(Paragraph('8.1.	Все дополнительные соглашения Сторон, акты и иные приложения к настоящему Договору, '
                          'подписываемые Сторонами при исполнении настоящего Договора, являются его неотъемлемой частью.', style))
    objs.append(Paragraph('8.2.	Настоящий Договор составлен в 2 (двух) экземплярах, имеющих одинаковую юридическую силу, '
                          'по одному для каждой из Сторон', style))
    # objs.append(Paragraph('9. АДРЕСА И РЕКВИЗИТЫ СТОРОН', styleCenter))

    styleAtr = deepcopy(style)
    styleAtr.firstLineIndent = 0
    f = ind.family
    n = ind.name[0:1]
    p = ind.patronymic[0:1]
    npf = n+'.'+' '+p+'.'+' '+f
    fio_director_list = exec_person.split(' ')
    print(fio_director_list)
    dir_f = fio_director_list[0]
    dir_n = fio_director_list[1]
    dir_p = fio_director_list[2]
    dir_npf = dir_n[0:1] + '.' + ' ' + dir_p[0:1] + '.' + ' ' + dir_f

    styleAtrEndStr = deepcopy(styleAtr)

    # styleAtrEndStr.spaceBefor = 5

    space_symbol = '&nbsp;'
    opinion = [
        [Paragraph('Исполнитель', styleAtr),
         Paragraph('', styleAtr),
         Paragraph('Пациент/Плательщик:', styleAtr)],
        [Paragraph('{} <br/>{}'.format(hospital_name,hospital_address), styleAtr),
         Paragraph('', styleAtr),
         Paragraph('{}<br/>Паспорт: {}-{}<br/>Адрес:{}'.format(individual_fio, document_passport_serial,
                                                        document_passport_num, ind_card.main_address),styleAtr)],
        [Paragraph('', styleAtr),Paragraph('', style),Paragraph('', styleAtr)],
        [Paragraph('Сотрудник {}'.format(hospital_short_name), styleAtr),
         Paragraph('', styleAtr),
         Paragraph('', styleAtr)],
        [Paragraph('________________________/{}/'.format(dir_npf), styleAtr),
         Paragraph('', styleAtr),
         Paragraph('/{}/________________________ <font face="Symbola" size=18>\u2713</font>'.format(npf), styleAtr)
         ],
    ]

    rowHeights = 5 * [None]
    rowHeights[4]=35
    tbl = Table(opinion, colWidths=(90 * mm, 10* mm, 90 * mm),rowHeights=rowHeights)

    tbl.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1.0, colors.white),
        ('TOPPADDING', (0, 0), (-1, -1), 1.5 * mm),
        ('VALIGN', (0, 0), (-1, -2), 'TOP'),
        ('VALIGN', (0, -1), (-1, -1), 'BOTTOM'),
        ('BOTTOMPADDING', (0, -1), (-1, -1), 4.2 * mm),
        ('BOTTOMPADDING', (0, -1), (0, -1), 1 * mm),

    ]))

    objs.append(Spacer(1, 2 * mm))

    objs.append(KeepTogether([Paragraph('9. АДРЕСА И РЕКВИЗИТЫ СТОРОН', styleCenter), tbl]))

    objs.append(Spacer(1,7 * mm))

    styleRight = deepcopy(style)
    styleRight.alignment = TA_RIGHT

    space_symbol = ' '

    qr_napr = ','.join([str(elem) for elem in result_data[3]])
    protect_val = SettingManager.get('protect_val')
    bstr = (qr_napr + protect_val).encode()
    protect_code = str(zlib.crc32(bstr))

    left_size_str = hospital_short_name +15 * space_symbol + protect_code + 15 * space_symbol

    qr_value = npf+'('+qr_napr+'),'+protect_code

    def first_pages(canvas, document):
        canvas.saveState()
        canvas.setFont("PTAstraSerifReg", 9)
        # вывести интерактивную форму "текст"
        form = canvas.acroForm
        # canvas.drawString(25, 780, '')
        form.textfield(name='comment', tooltip='comment',fontName='Times-Roman', fontSize=10,
                       x=57, y=750, borderStyle='underlined',borderColor=black, fillColor=white,
                       width=515, height=13, textColor=black, forceBorder=False)

        # Вывести на первой странице код-номер договора
        barcode128.drawOn(canvas, 120 * mm, 283 * mm)

        #вывести внизу QR-code (ФИО, (номера направлений))
        qr_code = qr.QrCodeWidget(qr_value)
        qr_code.barWidth = 70
        qr_code.barHeight = 70
        qr_code.qrVersion = 1
        bounds = qr_code.getBounds()
        width = bounds[2] - bounds[0]
        height = bounds[3] - bounds[1]
        d = Drawing()
        d.add(qr_code)
        renderPDF.draw(d, canvas, 90 * mm, 7)
        #вывести атрибуты для подписей
        canvas.setFont('PTAstraSerifReg', 10)
        canvas.drawString(40 * mm, 10 * mm, '____________________________')
        canvas.drawString(115 * mm, 10 * mm, '/{}/____________________________'.format(npf))
        canvas.setFont('Symbola', 18)
        canvas.drawString(195 * mm, 10 * mm, '\u2713')

        canvas.setFont('PTAstraSerifReg', 8)
        canvas.drawString(50 * mm, 7 * mm, '(подпись сотрудника)')
        canvas.drawString(160 * mm, 7 * mm, '(подпись плательщика)')

        #вывестии защитны вертикальный мелкий текст
        canvas.rotate(90)
        canvas.setFillColor(HexColor(0x4f4b4b))
        canvas.setFont('PTAstraSerifReg',5.2)
        canvas.drawString(10 * mm, -12 * mm, '{}'.format(6 * left_size_str))

        canvas.restoreState()

    def later_pages(canvas, document):
        canvas.saveState()
        #вывести внизу QR-code (ФИО, (номера направлений))
        qr_code = qr.QrCodeWidget(qr_value)
        qr_code.barWidth = 70
        qr_code.barHeight = 70
        qr_code.qrVersion = 1
        bounds = qr_code.getBounds()
        width = bounds[2] - bounds[0]
        height = bounds[3] - bounds[1]
        d = Drawing()
        d.add(qr_code)
        renderPDF.draw(d, canvas, 90 * mm, 7)
        #вывести атрибуты для подписей
        canvas.setFont('PTAstraSerifReg', 10)
        canvas.drawString(40 * mm, 10 * mm, '____________________________')
        canvas.drawString(115 * mm, 10 * mm, '/{}/____________________________'.format(npf))

        canvas.setFont('Symbola', 18)
        canvas.drawString(195 * mm, 10 * mm, '\u2713')

        canvas.setFont('PTAstraSerifReg', 8)
        canvas.drawString(50 * mm, 7 * mm, '(подпись сотрудника)')
        canvas.drawString(160 * mm, 7 * mm, '(подпись плательщика)')

        canvas.rotate(90)
        canvas.setFillColor(HexColor(0x4f4b4b))
        canvas.setFont('PTAstraSerifReg',5.2)
        canvas.drawString(10 * mm, -12 * mm, '{}'.format(6 * left_size_str))
        canvas.restoreState()

    doc.build(objs, onFirstPage=first_pages, onLaterPages=later_pages, canvasmaker=PageNumCanvas)

    pdf = buffer.getvalue()

    buffer.close()
    return pdf