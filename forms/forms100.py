from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Frame, PageTemplate, FrameBreak, Table, \
    TableStyle
from reportlab.platypus import PageBreak, NextPageTemplate, Indenter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle, StyleSheet1
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape, portrait
from reportlab.lib.units import mm
from copy import deepcopy
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT

from appconf.manager import SettingManager
from clients.models import Card, Document
from laboratory.settings import FONTS_FOLDER
import datetime
import locale
import sys
import pytils
import os.path
from io import BytesIO
from . import forms_func


# def form_100_01(**kwargs):
def form_01(request_data):
    """
    форма Пасопрт здоровья Приказ Министерства здравоохранения и социального развития РФ от 12 апреля 2011 г. N 302н
    """
    ind_card = Card.objects.get(pk=request_data["card_pk"])
    ind = ind_card.individual
    ind_doc = Document.objects.filter(individual=ind, is_active=True)

    hospital_name = "ОГАУЗ \"Иркутская медикосанитарная часть № 2\""
    hospital_address = "г. Иркутс, ул. Байкальская 201"
    hospital_kod_ogrn = "1033801542576"
    health_passport_num = "1"  # номер id patient из базы

    individual_sex = ind.sex
    individual_fio = ind.fio()
    individual_date_born = ind.bd()

    documents = forms_func.get_all_doc(ind_doc)
    document_passport_num = documents['passport']['num']
    document_passport_serial = documents['passport']['serial']
    document_passport_date_start = documents['passport']['date_start']
    document_passport_issued = documents['passport']['issued']
    document_polis = documents['polis']['num']
    document_snils = documents['snils']['num']

    indivudual_insurance_org="38014_ИРКУТСКИЙ ФИЛИАЛ АО \"СТРАХОВАЯ КОМПАНИЯ \"СОГАЗ-МЕД\" (Область Иркутская)"
    individual_benefit_code="_________"

    # card_attr = forms_func.get_card_attr(ind_card)
    ind_card_address = ind_card.main_address

    individual_work_organization = "Управление Федераньной службы по ветеринарному и фитосанитрному надзору по Иркутской области" \
                                   "и Усть-Ордынскому бурятскому автономному округу"  # реест организаций
    work_organization_okved = "91.5 - Обслуживание и ремонт компютерной и оргтехники, заправка картриджей" \
                              "обслуживание принтеров"
    individual_department = "отдел информационных технология, ораганизаци ремонта и обслуживания медицинского оборудования"
    individual_profession = "старший государственный таможенный инспектор"  # реест профессий

    list_result = ['Общ. анализ крови', 'Общ.анализ мочи', 'Глюкоза крови', 'Холестерин', 'RW', 'Флюорография', 'ЭКГ',
                   'Спирометрия', 'УЗИ м/желёз (маммогр.)', 'Аудиометрия', 'УЗИ огр.м/таза',
                   'Исслед. вестибулярн. аппарата',
                   'Исслед.вибрационн. чувствительности', 'Острота зрения', 'Рефрактометрия', 'Объём аккомодации',
                   'Исслед.бинокулярн. зрения',
                   'Цветоощущение', 'Офтальмотонометрия', 'Биомикроскопия сред глаза', 'Поля зрения',
                   'Бактериоскопия мазка',
                   'Офтальмоскопия глазного дня', 'Мазок из зева и носа', 'Ретикулоциты', 'АЛК или КП в моче',
                   'Метгемоглобины',
                   'Базальн. Зернист. Эритроцитов'
                   ]  # список лабораторных, инструментальных исследований
    list_doctor = ['Терапевт', 'Психиатр', 'Нарколог', 'Гинеколог', 'Офтальмолог', 'Лор', 'Невролог', 'Дерматолог',
                   'Хирург', 'Стоматолог']  # список врачей-специалистов

    for i in range(0, 3):
        list_doctor.append('')

    if sys.platform == 'win32':
        locale.setlocale(locale.LC_ALL, 'rus_rus')
    else:
        locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')

    pdfmetrics.registerFont(TTFont('PTAstraSerifBold', os.path.join(FONTS_FOLDER, 'PTAstraSerif-Bold.ttf')))
    pdfmetrics.registerFont(TTFont('PTAstraSerifReg', os.path.join(FONTS_FOLDER, 'PTAstraSerif-Regular.ttf')))
    # http://www.cnews.ru/news/top/2018-12-10_rossijskim_chinovnikam_zapretili_ispolzovat
    # Причина PTAstraSerif использовать

    buffer = BytesIO()

    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            leftMargin=10 * mm,
                            rightMargin=10 * mm, topMargin=10 * mm,
                            bottomMargin=10 * mm, allowSplitting=1,
                            title="Форма {}".format("Паспорт здоровья"))
    width, height = landscape(A4)
    styleSheet = getSampleStyleSheet()
    style = styleSheet["Normal"]
    style.fontName = "PTAstraSerifBold"
    style.fontSize = 9
    style.leading = 6
    styleBold = deepcopy(style)
    styleBold.fontName = "PTAstraSerifBold"
    styleCenter = deepcopy(style)
    styleCenter.alignment = TA_CENTER
    styleCenterBold = deepcopy(styleBold)
    styleCenterBold.alignment = TA_CENTER
    styleJustified = deepcopy(style)
    styleJustified.alignment = TA_JUSTIFY
    styleJustified.spaceAfter = 4.5 * mm
    styleJustified.fontSize = 12
    styleJustified.leading = 4.5 * mm

    righ_frame = Frame(148.5 * mm, 0 * mm, width=148.5 * mm, height=210 * mm,
                       leftPadding=10 * mm, bottomPadding=6, rightPadding=10 * mm, topPadding=6, showBoundary=1)
    left_frame = Frame(0 * mm, 0 * mm, width=148.5 * mm, height=210 * mm,
                       leftPadding=10 * mm, bottomPadding=6, rightPadding=10 * mm, topPadding=6, showBoundary=1)
    doc.addPageTemplates(PageTemplate(id='TwoCol', frames=[righ_frame, left_frame], pagesize=landscape(A4)))

    space = 5.5 * mm
    objs = [
        Spacer(1, 3 * mm),
        Paragraph('<font face="PTAstraSerifBold">Министерство здравоохранения Российской Федерации</font>',
                  styleCenter),
        Spacer(1, 3 * mm),
        Paragraph('<font face="PTAstraSerifBold"><u>{}</u></font>'.format(hospital_name), styleCenter),
        Spacer(1, 2 * mm),
        Paragraph('<font face="PTAstraSerifReg"><font size=9>(наименование медицинской организации)</font></font>',
                  styleCenter),
        Spacer(1, 3 * mm),
        Paragraph('<font face="PTAstraSerifBold"><u>{}</u></font>'.format(hospital_address), styleCenter),
        Spacer(1, 5 * mm),
        Paragraph('<font face="PTAstraSerifBold" size=12>Код ОГРН {}</font>'.format(hospital_kod_ogrn), styleCenter),
        Spacer(1, 10 * mm),
        Paragraph('<font face="PTAstraSerifBold" size=12>ПАСПОРТ ЗДОРОВЬЯ РАБОТНИКА № <u>{}</u></font>'.
                  format(health_passport_num), styleCenter),
        Spacer(1, space),
        Paragraph('<font face="PTAstraSerifReg"size=10><u>{} года</u></font>'.
                  format(pytils.dt.ru_strftime(u"%d %B %Y", inflected=True, date=datetime.datetime.now())),
                  styleCenter),
        Spacer(1, 7),
        Paragraph('<font face="PTAstraSerifReg" size=7>(дата оформления)</font>', styleCenter),
        Spacer(1, space),
        Paragraph('<font face="PTAstraSerifReg">1.Фамилия, имя, отчество:'
                  '<u>{}</u> </font>'.format(individual_fio), styleJustified),
        Paragraph('<font face="PTAstraSerifReg">2.Пол: <u>{}</u> <img src="forms/img/FFFFFF-space.png" width="90" />'
                  '3.Дата Рождения: <u>{}</u> </font>'.format(individual_sex, individual_date_born), styleJustified),
        Paragraph('<font face="PTAstraSerifReg">4.Паспорт: серия <u>{}</u> <img src="forms/img/FFFFFF-space.png" width="25"/>'
                  'номер: <u>{}</u></font>'.format(document_passport_serial, document_passport_num), styleJustified),
        Paragraph('<font face="PTAstraSerifReg">Дата выдачи: <u>{}</u></font>'.format(document_passport_date_start),
                  styleJustified),
        Paragraph('<font face="PTAstraSerifReg"> Кем Выдан: <u>{}</u></font>'.format(document_passport_issued), styleJustified),
        Paragraph('<font face="PTAstraSerifReg">5. Адрес регистрации по месту жительства (пребывания):'
                  ' <u>{}</u></font>'.format(ind_card_address), styleJustified),
        Paragraph('<font face="PTAstraSerifReg">6. Номер страхового полиса(ЕНП):'
                  ' <u>{}</u></font>'.format(document_polis), styleJustified),
        Paragraph('<font face="PTAstraSerifReg">7. Наименование работодателя:'
                  ' <u>{}</u></font>'.format(individual_work_organization), styleJustified),
        Paragraph('<font face="PTAstraSerifReg">7.1 Форма собственности и вид экономической деятельности '
                  'работодателя по ОКВЭД: <u>{}</u></font>'.format(work_organization_okved), styleJustified),
        Paragraph('<font face="PTAstraSerifReg">7.2  Наименование структурного подразделения (цех, участок, отдел):'
                  ' <u> {} </u></font>'.format(individual_department), styleJustified),
        Paragraph('<font face="PTAstraSerifReg">8. Профессия (должность) (в настоящее время):'
                  ' <u>{}</u></font>'.format(individual_profession), styleJustified),
        FrameBreak(),
        Spacer(1, space),
        Paragraph('<font face="PTAstraSerifReg">12. Заключение:</font>', styleJustified),
    ]
    styleT = deepcopy(style)
    styleT.alignment = TA_CENTER
    styleT.fontSize = 10
    styleT.leading = 4.5 * mm

    opinion = [
        [Paragraph('<font face="PTAstraSerifReg">Заключение по результатам предварительного '
                   'и периодического медицинского осмотра</font>', styleT),
         Paragraph('<font face="PTAstraSerifReg">Дата получения заключения</font>', styleT),
         Paragraph('<font face="PTAstraSerifReg"> Подпись профпатолога</font>', styleT)],
    ]

    for i in range(0, 5):
        para = [Paragraph('<font face="PTAstraSerifReg" size=11>Профпригоден/\nпрофнепригоден</font>', styleT)]
        opinion.append(para)

    tbl = Table(opinion, colWidths=(48 * mm, 40 * mm, 40 * mm), hAlign='LEFT', style=[
        ('GRID', (0, 0), (-1, -1), 0.7, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 1.5 * mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1.5 * mm),

    ])

    objs.append(tbl)

    objs.append(Spacer(1, 10 * mm))
    objs.append(Paragraph('<font face="PTAstraSerifReg">Для заметок:</font>', styleJustified))

    s = "___________________________________________________________"
    for i in range(0, 6):
        objs.append(Spacer(1, 1 * mm))
        objs.append(Paragraph('<font face="PTAstraSerifReg">{}</font>'.format(s), styleJustified))

    objs.append(NextPageTemplate("TwoCol"))
    objs.append(FrameBreak())
    objs.append(Spacer(1, 7 * mm))
    objs.append(Paragraph('<font face="PTAstraSerifReg">11. Результаты лабораторных и инструментальных исследований'
                          '</font>', styleJustified))

    tbl_result = [
        [Paragraph('<font face="PTAstraSerifReg" size=11>Вид исследования</font>', styleT),
         Paragraph('<font face="PTAstraSerifReg" size=11>Даты исследований</font>', styleT),
         '', '', '', ''],
        ['', '', '', '', '', '']
    ]

    styleTR = deepcopy(styleT)
    styleTR.alignment = TA_LEFT
    styleTR.fontSize = 11
    styleTR.spaceAfter = 12 * mm

    for i in list_result:
        para = [Paragraph('<font face="PTAstraSerifReg">{}</font>'.format(i), styleTR)]
        tbl_result.append(para)

    tbl = Table(tbl_result, colWidths=(41 * mm, 22 * mm, 17 * mm, 17 * mm, 17 * mm, 17 * mm), hAlign='LEFT', style=[
        ('GRID', (0, 0), (-1, -1), 0.7, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 0.01 * mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0.01 * mm),
        ('SPAN', (0, 0), (0, 1)),
        ('SPAN', (1, 0), (-1, 0)),
    ])
    objs.append(tbl)

    objs.append(FrameBreak())
    objs.append(Spacer(1, 7 * mm))
    objs.append(Paragraph('<font face="PTAstraSerifReg">9. Условия труда в настоящее время</font>', styleJustified))

    tbl_result = [
        [Paragraph('<font face="PTAstraSerifReg" size=10>Наименование производственного фактора, вида работы с '
                   'указанием пункта</font>', styleT),
         Paragraph('<font face="PTAstraSerifReg" size=10>Стаж работы с фактором</font>', styleT), ]
    ]
    for i in range(0, 4):
        para = ['', '']
        tbl_result.append(para)

    row_height = []
    for i in tbl_result:
        row_height.append(8 * mm)

    row_height[0] = None
    tbl = Table(tbl_result, colWidths=(75 * mm, 55 * mm), rowHeights=row_height, hAlign='LEFT', style=[
        ('GRID', (0, 0), (-1, -1), 0.7, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 0.01 * mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0.01 * mm),
        ('LEFTPADDING ', (0, 2), (0, -1), 0.1 * mm),
        ('SPAN', (1, 1), (1, -1)),
    ])

    objs.append(tbl)

    objs.append(Spacer(1, 5 * mm))

    styleDoc = deepcopy(styleJustified)
    styleDoc.spaceAfter = 1 * mm
    objs.append(Paragraph('<font face="PTAstraSerifReg">10. Заключения врачей - специалистов:</font>', styleDoc, ))
    tbl_result = [
        [Paragraph('<font face="PTAstraSerifReg" size=11>Врач-специалист</font>', styleT),
         Paragraph('<font face="PTAstraSerifReg" size=11>Даты исследований</font>', styleT),
         '', '', '', ''],
        ['', '', '', '', '', '']
    ]

    for i in list_doctor:
        para = [Paragraph('<font face="PTAstraSerifReg">{}</font>'.format(i), styleTR)]
        tbl_result.append(para)

    row_height = []
    for i in tbl_result:
        row_height.append(9 * mm)

    row_height[0] = None
    row_height[1] = None
    tbl = Table(tbl_result, colWidths=(41 * mm, 22 * mm, 17 * mm, 17 * mm, 17 * mm, 17 * mm), rowHeights=row_height,
                hAlign='LEFT', style=[
            ('GRID', (0, 0), (-1, -1), 0.7, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 0.01 * mm),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0.01 * mm),
            ('LEFTPADDING ', (0, 2), (0, -1), 0.1 * mm),
            ('SPAN', (0, 0), (0, 1)),
            ('SPAN', (1, 0), (-1, 0)),
        ])
    objs.append(tbl)

    doc.build(objs)

    pdf = buffer.getvalue()
    buffer.close()
    return pdf


def form_02(request_data):
    """
    Форма 025/у - титульный лист амбулаторной карты
    Приказ Минздрава России от 15.12.2014 N 834н (ред. от 09.01.2018)
    """
    ind_card = Card.objects.get(pk=request_data["card_pk"])
    ind = ind_card.individual
    ind_doc = Document.objects.filter(individual=ind, is_active=True)

    hospital_name = SettingManager.get("org_title")
    hospital_address = SettingManager.get("org_address")
    hospital_kod_ogrn = SettingManager.get("org_ogrn", "<TODO:OGRN>")
    hospital_okpo = SettingManager.get("org_ogrn", "<TODO:OKPO>")

    individual_fio = ind.fio()
    individual_sex = ind.sex
    individual_date_born = ind.bd()

    document_passport = "Паспорт РФ"

    documents = forms_func.get_all_doc(ind_doc)
    document_passport_num = documents['passport']['num']
    document_passport_serial = documents['passport']['serial']
    document_passport_date_start = documents['passport']['date_start']
    document_passport_issued = documents['passport']['issued']
    document_polis = documents['polis']['num']
    document_snils = documents['snils']['num']

    indivudual_insurance_org = documents['polis']['issued']
    individual_benefit_code = "_________"

    ind_card_num = ind_card.number_with_type()
    ind_card_address = ind_card.main_address
    ind_card_phone = ", ".join(ind_card.get_phones())

    individual_work_organization = "Управление Федераньной службы по ветеринарному и фитосанитрному надзору по Иркутской области" \
                                   "и Усть-Ордынскому бурятскому автономному округу"  # реест организаций
    work_organization_okved = "91.5 - Обслуживание и ремонт компютерной и оргтехники, заправка картриджей" \
                              "обслуживание принтеров"
    individual_department = "отдел информационных технология, ораганизаци ремонта и обслуживания медицинского оборудования"
    individual_profession = "старший государственный таможенный инспектор"  # реест профессий

    if sys.platform == 'win32':
        locale.setlocale(locale.LC_ALL, 'rus_rus')
    else:
        locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')

    pdfmetrics.registerFont(TTFont('PTAstraSerifBold', os.path.join(FONTS_FOLDER, 'PTAstraSerif-Bold.ttf')))
    pdfmetrics.registerFont(TTFont('PTAstraSerifReg', os.path.join(FONTS_FOLDER, 'PTAstraSerif-Regular.ttf')))
    # http://www.cnews.ru/news/top/2018-12-10_rossijskim_chinovnikam_zapretili_ispolzovat
    # Причина PTAstraSerif использовать

    buffer = BytesIO()
    individual_fio = ind.fio()
    individual_date_born = ind.bd()

    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            leftMargin=25 * mm,
                            rightMargin=5 * mm, topMargin=6 * mm,
                            bottomMargin=6 * mm, allowSplitting=1,
                            title="Форма {}".format("025/у"))
    width, height = portrait(A4)
    styleSheet = getSampleStyleSheet()
    style = styleSheet["Normal"]
    style.fontName = "PTAstraSerifReg"
    style.fontSize = 10
    style.leading = 12
    style.spaceAfter = 0.5 * mm
    styleBold = deepcopy(style)
    styleBold.fontName = "PTAstraSerifBold"
    styleCenter = deepcopy(style)
    styleCenter.alignment = TA_CENTER
    styleCenter.fontSize = 12
    styleCenter.leading = 15
    styleCenter.spaceAfter = 1 * mm
    styleCenterBold = deepcopy(styleBold)
    styleCenterBold.alignment = TA_CENTER
    styleCenterBold.fontSize = 12
    styleCenterBold.leading = 15
    styleCenterBold.face = 'PTAstraSerifBold'
    styleJustified = deepcopy(style)
    styleJustified.alignment = TA_JUSTIFY
    styleJustified.spaceAfter = 4.5 * mm
    styleJustified.fontSize = 12
    styleJustified.leading = 4.5 * mm

    objs = []

    styleT = deepcopy(style)
    styleT.alignment = TA_LEFT
    styleT.fontSize = 10
    styleT.leading = 4.5 * mm
    styleT.face ='PTAstraSerifReg'

    opinion = [
        [Paragraph('<font size=11>{}<br/>Адрес: {}<br/>ОГРН: {} </font>'.format(
            hospital_name,hospital_address,hospital_kod_ogrn), styleT),
         Paragraph('<font size=9 >Код формы по ОКУД:<br/>Код организации по ОКПО: 31348613<br/>'
                   'Медицинская документация<br/>Учетная форма № 025/у</font>', styleT)],
    ]

    tbl = Table(opinion, 2 * [90 * mm])

    tbl.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.75, colors.white),
        ('LEFTPADDING', (1, 0), (-1, -1), 80),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

    objs.append(tbl)
    space_symbol = '&nbsp;'
    content_title =[
        Indenter(left=0 *mm),
        Spacer(1, 4 * mm),
        Paragraph('МЕДИЦИНСКАЯ КАРТА ПАЦИЕНТА, <br/> ПОЛУЧАЮЩЕГО МЕДИЦИНСКУЮ ПОМОЩЬ В АМБУЛАТОРНЫХ УСЛОВИЯХ', styleCenter),
        Paragraph('{}№&nbsp;{}'.format(3 * space_symbol, ind_card_num), styleCenterBold),
        Spacer(1, 2 * mm),
        Paragraph('1.Дата заполнения медицинской карты: {}'.
                  format(pytils.dt.ru_strftime(u"%d %B %Y", inflected=True, date=datetime.datetime.now())), style),
        Paragraph("2. Фамилия, имя, отчество:<b> {} </b> ".format(individual_fio), style),
        Paragraph('3. Пол: {} {} 4. Дата рождения: {}'.format(individual_sex, 3 * space_symbol, individual_date_born), style),
        Paragraph('5. Место регистрации: {}'.format(ind_card_address), style),
        Paragraph('тел. {}'.format(ind_card_phone), style),
        Paragraph('6. Местность: городская — 1, сельская — 2', style),
        Paragraph('7. Полис ОМС: серия______№: {} {}'
                  '8. СНИЛС: {}'.format(document_polis, 13 * space_symbol, document_snils),style),
        Paragraph('9. Наименование страховой медицинской организации: {}'.format(indivudual_insurance_org), style),
        Paragraph('10. Код категории льготы: {} {} 11. Документ: {} &nbsp; серия: {} &nbsp;&nbsp; №: {}'.
                  format(individual_benefit_code, 35 * space_symbol, document_passport, document_passport_serial, document_passport_num), style),
        Paragraph('12. Заболевания, по поводу которых осуществляется диспансерное наблюдение:', style),
        Spacer(1,2 * mm),
    ]

    objs.extend(content_title)

    styleTCenter = deepcopy(styleT)
    styleTCenter.alignment=TA_CENTER
    styleTCenter.leading = 3.5 * mm

    opinion=[
        [Paragraph('<font size=9>Дата начала диспансерного наблюдения </font>', styleTCenter),
         Paragraph('<font size=9 >Дата прекращения диспансерного наблюдения</font>', styleTCenter),
         Paragraph('<font size=9 >Диагноз</font>', styleTCenter),
         Paragraph('<font size=9 >Код по МКБ-10</font>', styleTCenter),
         Paragraph('<font size=9 >Врач</font>', styleTCenter),
         ],
    ]
    for i in range(0, 5):
        para = ['', '', '', '', '']
        opinion.append(para)

    row_height = []
    for i in opinion:
        row_height.append(6 * mm)

    row_height[0] = None

    tbl = Table(opinion, colWidths=(27 * mm, 30 * mm, 75 * mm, 20 * mm, 27 * mm), rowHeights=row_height)

    tbl.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1.0, colors.black),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),

        ]))

    objs.append(tbl)
    doc.build(objs)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf
