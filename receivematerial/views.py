# coding=utf8
from django.core.paginator import Paginator
from django.shortcuts import render
from django.utils import dateformat

from laboratory import settings
from podrazdeleniya.models import Podrazdeleniya, Subgroups
from directions.models import Napravleniya, Issledovaniya, IstochnikiFinansirovaniya, TubesRegistration
from django.http import HttpResponse
from users.models import DoctorProfile
import simplejson as json
from datetime import datetime, date
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from laboratory.decorators import group_required
import slog.models as slog
import directory.models as directory

@csrf_exempt
@login_required
@group_required("Получатель биоматериала")
def receive(request):
    """Представление для приемщика материала в лаборатории"""
    from django.utils import timezone

    if request.method == "GET":
        groups = Subgroups.objects.filter(
            podrazdeleniye=request.user.doctorprofile.podrazileniye)  # Список доступных групп для текущего пользователя
        podrazdeleniya = Podrazdeleniya.objects.filter(isLab=False, hide=False).order_by(
            "title")  # Список всех подразделений
        return render(request, 'dashboard/receive.html', {"groups": groups, "podrazdeleniya": podrazdeleniya})
    else:
        tubes = json.loads(request.POST["data"])
        for tube_get in tubes:
            tube = TubesRegistration.objects.get(id=tube_get["id"])
            if tube_get["status"]:
                tube.set_r(request.user.doctorprofile)
            elif tube_get["notice"] != "":
                tube.set_notice(request.user.doctorprofile, tube_get["notice"])

        result = {"r": True}
        return HttpResponse(json.dumps(result), content_type="application/json")


@csrf_exempt
@login_required
@group_required("Получатель биоматериала")
def receive_obo(request):
    if request.method == "GET":
        return render(request, 'dashboard/receive_one-by-one.html')
    if request.POST["pk"].isdigit():
        pk = int(request.POST["pk"])
        if TubesRegistration.objects.filter(pk=pk).exists() and Issledovaniya.objects.filter(tubes__id=pk).exists():
            tube = TubesRegistration.objects.get(pk=pk)
            if tube.issledovaniya_set.first().research.subgroup.podrazdeleniye == request.user.doctorprofile.podrazileniye:
                status = tube.day_num(request.user.doctorprofile, int(request.POST["num"]))
                result = {"r": 1, "n": status["n"], "new": status["new"],
                          "receivedate": tube.time_recive.strftime("%d.%m.%Y"),
                          "researches": [x.research.title for x in Issledovaniya.objects.filter(tubes__id=pk)]}
            else:
                result = {"r": 2, "lab": str(tube.issledovaniya_set.first().research.subgroup.podrazdeleniye)}
        else:
            result = {"r": 3}
    else:
        result = {"r": 3}
    return HttpResponse(json.dumps(result), content_type="application/json")


@csrf_exempt
@login_required
@group_required("Получатель биоматериала")
def receive_history(request):
    from django.utils import timezone, datetime_safe
    result = {"rows": []}
    date1 = datetime_safe.datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
    date2 = datetime_safe.datetime.now()
    for row in TubesRegistration.objects.filter(time_recive__range=(date1, date2),
                                                doc_recive=request.user.doctorprofile).order_by("-daynum"):
        result["rows"].append(
            {"pk": row.pk, "n": row.daynum or 0, "type": str(row.type.tube), "color": row.type.tube.color,
             "researches": [x.research.title for x in Issledovaniya.objects.filter(tubes__id=row.id)]})
    return HttpResponse(json.dumps(result), content_type="application/json")


@csrf_exempt
@login_required
@group_required("Получатель биоматериала")
def last_received(request):
    from django.utils import datetime_safe
    date1 = datetime_safe.datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
    date2 = datetime_safe.datetime.now()
    last_num = 0
    if TubesRegistration.objects.filter(time_recive__range=(date1, date2), daynum__gt=0,
                                        issledovaniya__research__subgroup__podrazdeleniye=request.user.doctorprofile.podrazileniye).exists():
        last_num = max([x.daynum for x in
                        TubesRegistration.objects.filter(time_recive__range=(date1, date2), daynum__gt=0,
                                                         issledovaniya__research__subgroup__podrazdeleniye=request.user.doctorprofile.podrazileniye)])
    return HttpResponse(json.dumps({"last_n": last_num}), content_type="application/json")


@csrf_exempt
@login_required
@group_required("Получатель биоматериала")
def receive_execlist(request):
    import datetime
    import directory.models as directory
    from reportlab.graphics import renderPDF
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfdoc
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import landscape
    from reportlab.pdfbase import pdfdoc
    from django.core.paginator import Paginator
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.units import mm
    import os.path
    from io import BytesIO
    from django.utils import timezone, datetime_safe
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Table, TableStyle
    from reportlab.lib import colors
    from reportlab.platypus import Paragraph

    PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
    pdfmetrics.registerFont(
        TTFont('OpenSans', PROJECT_ROOT + '/../static/fonts/OpenSans.ttf'))
    pdfmetrics.registerFont(
        TTFont('OpenSansB', PROJECT_ROOT + '/../static/fonts/OpenSans-Bold.ttf'))

    w, h = landscape(A4)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="execlist.pdf"'
    pdfdoc.PDFCatalog.OpenAction = '<</S/JavaScript/JS(this.print\({bUI:true,bSilent:false,bShrinkToFit:true}\);)>>'

    date = request.GET["date"]
    date = datetime.date(int(date.split(".")[2]), int(date.split(".")[1]), int(date.split(".")[0]))
    researches = json.loads(request.GET["researches"])
    buffer = BytesIO()

    c = canvas.Canvas(buffer, pagesize=landscape(A4))

    marginx = 15 * mm
    marginy = 10 * mm

    pw = w - marginx * 2
    ph = h - marginy * 2

    from datetime import timedelta
    date1 = date
    date2 = date1 + timedelta(days=1)

    def py(y=0):
        y *= mm
        return h - y - marginy

    def px(x=0):
        x *= mm
        return x + marginx

    def pxc(x=0):
        x *= mm
        return w / 2 + x

    def pxr(x=0):
        x *= mm
        return pw - x + marginx

    for pk in researches:
        if directory.Researches.objects.filter(pk=pk).exists() and Issledovaniya.objects.filter(research__pk=pk,
                                                                                                tubes__time_recive__range=(
                                                                                                date1, date2),
                                                                                                research__subgroup__podrazdeleniye=request.user.doctorprofile.podrazileniye).exists():
            research = directory.Researches.objects.get(pk=pk)
            fractions = [x.title for x in directory.Fractions.objects.filter(research=research)]
            tubes = [x.pk for x in TubesRegistration.objects.filter(time_recive__range=(date1, date2),
                                                                    doc_recive=request.user.doctorprofile,
                                                                    issledovaniya__research=research).order_by(
                "daynum")]
            pages = Paginator(tubes, 16)
            for pg_num in pages.page_range:
                c.setFont('OpenSans', 12)
                c.drawString(px(), py(), "Лист исполнения - %s за %s" % (research.title, date1.strftime("%d.%m.%Y")))
                c.drawRightString(pxr(), py(), research.subgroup.podrazdeleniye.title)
                c.drawString(px(), 6 * mm, "Страница %d из %d" % (pg_num, pages.num_pages))

                styleSheet = getSampleStyleSheet()

                tw = pw

                data = []
                tmp = []
                tmp.append(Paragraph('<font face="OpenSansB" size="8">№</font>', styleSheet["BodyText"]))
                tmp.append(Paragraph('<font face="OpenSansB" size="8">ФИО, № истории</font>', styleSheet["BodyText"]))
                tmp.append(Paragraph('<font face="OpenSansB" size="8">№ мат.</font>', styleSheet["BodyText"]))
                for fraction in fractions:
                    fraction = fraction[:int(100 / len(fractions))]
                    tmp.append(
                        Paragraph('<font face="OpenSansB" size="6">%s</font>' % fraction, styleSheet["BodyText"]))
                data.append(tmp)

                pg = pages.page(pg_num)
                for tube_pk in pg.object_list:
                    tube = TubesRegistration.objects.get(pk=tube_pk)
                    napravleniye = Issledovaniya.objects.filter(tubes__pk=tube_pk).first().napravleniye
                    tmp = []
                    tmp.append(
                        Paragraph('<font face="OpenSans" size="8">%d</font>' % (tube.daynum), styleSheet["BodyText"]))
                    tmp.append(Paragraph('<font face="OpenSans" size="8">%s</font>' % (napravleniye.client.fio() + (
                    "" if not napravleniye.history_num or napravleniye.history_num == "" else ", " + napravleniye.history_num)),
                                         styleSheet["BodyText"]))
                    tmp.append(
                        Paragraph('<font face="OpenSans" size="8">%d</font>' % (tube_pk), styleSheet["BodyText"]))
                    for _ in fractions:
                        tmp.append(Paragraph('<font face="OpenSans" size="8"></font>', styleSheet["BodyText"]))
                    data.append(tmp)

                cw = [int(tw * 0.07), int(tw * 0.245), int(tw * 0.045)]
                lw = tw * 0.67
                for _ in range(0, len(fractions) + 1):
                    cw.append(lw / len(fractions))
                t = Table(data, colWidths=cw)
                t.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                       ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                                       ('TEXTCOLOR', (0, -1), (-1, -1), colors.black),
                                       ('INNERGRID', (0, 0), (-1, -1), 0.8, colors.black),
                                       ('BOX', (0, 0), (-1, -1), 0.8, colors.black),
                                       ('LEFTPADDING', (0, 0), (-1, -1), 2),
                                       ('TOPPADDING', (0, 0), (-1, -1), 9),
                                       ('RIGHTPADDING', (0, 0), (-1, -1), 1),
                                       ('BOTTOMPADDING', (0, 0), (-1, -1), 9),
                                       ]))
                t.canv = c
                wt, ht = t.wrap(0, 0)
                t.drawOn(c, px(), py(5) - ht)

                c.showPage()
    c.save()
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    return response


@login_required
def tubes_get(request):
    """ Получение списка не принятых пробирок """
    result = []
    k = set()
    if request.method == "GET":
        subgroup_lab = Subgroups.objects.get(pk=request.GET["subgroup"])
        podrazledeniye = Podrazdeleniya.objects.get(pk=request.GET["from"])
        date_start = request.GET["datestart"]
        date_end = request.GET["dateend"]
        import datetime
        date_start = datetime.date(int(date_start.split(".")[2]), int(date_start.split(".")[1]),
                                   int(date_start.split(".")[0]))
        date_end = datetime.date(int(date_end.split(".")[2]), int(date_end.split(".")[1]),
                                 int(date_end.split(".")[0])) + datetime.timedelta(1)
        for tube in TubesRegistration.objects.filter(doc_get__podrazileniye=podrazledeniye, notice="",
                                                     doc_recive__isnull=True, time_get__range=(date_start, date_end),
                                                     issledovaniya__research__subgroup=subgroup_lab):
            if tube.getbc() in k or tube.rstatus(): continue
            issledovaniya_tmp = []
            for iss in Issledovaniya.objects.filter(tubes__id=tube.id, research__subgroup=subgroup_lab,
                                                    tubes__time_get__range=(date_start, date_end)):
                issledovaniya_tmp.append(iss.research.title)
            if len(issledovaniya_tmp) > 0:
                k.add(tube.getbc())
                result.append({"researches": ' | '.join(issledovaniya_tmp),
                               "direction": tube.issledovaniya_set.first().napravleniye.pk,
                               "tube": {"type": tube.type.tube.title, "id": tube.getbc(), "status": tube.rstatus(),
                                        "color": tube.type.tube.color, "notice": tube.notice}})

    return HttpResponse(json.dumps(list(result)), content_type="application/json")


from reportlab.lib.pagesizes import A4

w, h = A4


@login_required
def receive_journal(request):
    """Печать истории принятия материала за день"""
    user = request.user.doctorprofile  # Профиль текущего пользователя
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Table, TableStyle
    from reportlab.lib import colors
    from reportlab.platypus import Paragraph
    from reportlab.lib.styles import getSampleStyleSheet

    styleSheet = getSampleStyleSheet()
    import os.path
    import collections
    import pytz
    import copy

    start = "1"  # str(request.GET.get("start", "1"))
    group = str(request.GET.get("group", "-2"))
    return_type = str(request.GET.get("return", "pdf"))
    otd = str(request.GET.get("otd", "-1"))

    start = 1 if not start.isdigit() else int(start)
    group = -2 if group not in ["-2", "-1"] and (not group.isdigit() or not directory.ResearchGroup.objects.filter(pk=int(group)).exists()) else int(group)
    otd = int(otd)

    PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))  # Директория Django
    pdfmetrics.registerFont(TTFont('OpenSans', PROJECT_ROOT + '/../static/fonts/OpenSans.ttf'))  # Загрузка шрифта

    response = HttpResponse(content_type='application/pdf')  # Формирование ответа
    response[
        'Content-Disposition'] = 'inline; filename="napr.pdf"'  # Content-Disposition inline для показа PDF в браузере
    from io import BytesIO
    buffer = BytesIO()  # Буфер
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(buffer, pagesize=A4)  # Холст
    tubes = []
    if otd <= -1:
        tubes = TubesRegistration.objects.filter(
            issledovaniya__research__subgroup__podrazdeleniye=request.user.doctorprofile.podrazileniye,
            time_recive__gte=datetime.now().date(), doc_recive__isnull=False).order_by(
            'issledovaniya__napravleniye__client__pk')
    elif otd > -1:
        tubes = TubesRegistration.objects.filter(
            issledovaniya__research__subgroup__podrazdeleniye=request.user.doctorprofile.podrazileniye,
            time_recive__gte=datetime.now().date(), doc_get__podrazileniye__pk=otd, doc_recive__isnull=False).order_by(
            'issledovaniya__napravleniye__client__pk')

    local_tz = pytz.timezone(settings.TIME_ZONE)  # Локальная временная зона
    labs = {}  # Словарь с пробирками, сгруппироваными по лаборатории
    directions = set()
    vids = set()

    perpage = 47

    n = 1
    for v in tubes:  # Перебор пробирок
        idv = v.id
        if idv in vids: continue
        vids.add(idv)
        iss = Issledovaniya.objects.filter(tubes__id=v.id) # Получение исследований для пробирки

        if group == -1:
            iss = iss.filter(research__groups__isnull=True)
        elif group >= 0:
            iss = iss.filter(research__groups__pk=group)

        iss_list = collections.OrderedDict()  # Список исследований

        k = str(v.doc_get.podrazileniye.pk) + "@" + str(v.doc_get.podrazileniye)

        for val in iss.order_by("research__sort_weight"):  # Цикл перевода полученных исследований в список
            iss_list[val.research.sort_weight] = val.research.title

        if len(iss_list) == 0:
            continue
        if n < start:
            n += 1
            continue

        directions.add(iss[0].napravleniye.pk)
        if return_type == "pdf":
            if k not in labs.keys():  # Добавление списка в словарь если по ключу k нету ничего в словаре labs
                labs[k] = []

            if perpage - len(labs[k]) % perpage < len(iss_list):
                pre = copy.deepcopy(labs[k][len(labs[k]) - 1])
                pre["researches"] = ""
                for x in range(0, perpage - len(labs[k]) % perpage):
                    labs[k].append(pre)
            for value in iss_list:  # Перебор списка исследований
                labs[k].append(
                    {"type": v.type.tube.title, "researches": iss_list[value],
                     "client-type": iss[0].napravleniye.client.type,
                     "lab_title": iss[0].research.subgroup.title,
                     "time": "" if not v.time_recive else v.time_recive.astimezone(local_tz).strftime("%H:%M:%S"),
                     "dir_id": iss[0].napravleniye.pk,
                     "podr": iss[0].napravleniye.doc.podrazileniye.title,
                     "receive_n": str(n),
                     "tube_id": str(v.id),
                     "direction": str(iss[0].napravleniye.pk),
                     "history_num": iss[0].napravleniye.history_num,
                     "fio": iss[
                         0].napravleniye.client.shortfio()})  # Добавление в список исследований и пробирок по ключу k в словарь labs
        n += 1
    directions = list(directions)
    if return_type == "directions":
        return HttpResponse(json.dumps(directions), content_type="application/json")

    labs = collections.OrderedDict(sorted(labs.items()))  # Сортировка словаря
    c.setFont('OpenSans', 20)

    paddingx = 17
    data_header = ["№", "ФИО, № истории", "№ Напр", "№ емкости", "Тип емкости", "Наименования исследований"]
    tw = w - paddingx * 3.5
    tx = paddingx * 2
    ty = 90
    c.setFont('OpenSans', 9)
    styleSheet["BodyText"].fontName = "OpenSans"
    styleSheet["BodyText"].fontSize = 7
    doc_num = 0

    for key in labs:
        doc_num += 1
        p = Paginator(labs[key], perpage)
        i = 0
        if doc_num >= 2:
            c.showPage()

        nn = 0

        gid = "-1"
        for pg_num in p.page_range:
            pg = p.page(pg_num)
            if pg_num >= 0:
                drawTituls(c, user, p.num_pages, pg_num, paddingx, pg[0], group=group, otd=key.split("@")[1])
            data = []
            tmp = []
            for v in data_header:
                tmp.append(Paragraph(str(v), styleSheet["BodyText"]))
            data.append(tmp)
            merge_list = {}
            num = 0
            lastid = "-1"
            for obj in pg.object_list:
                tmp = []
                if lastid != obj["tube_id"]:
                    if gid != obj["tube_id"]:
                        i += 1
                    lastid = gid = obj["tube_id"]
                    shownum = True
                else:
                    shownum = False
                    if lastid not in merge_list.keys():
                        merge_list[lastid] = []
                    merge_list[lastid].append(num)

                if shownum:
                    nn += 1
                    tmp.append(Paragraph(str(nn), styleSheet[
                        "BodyText"]))  # "--" if obj["receive_n"] == "0" else obj["receive_n"], styleSheet["BodyText"]))
                    fio = obj["fio"]
                    if obj["history_num"] and len(obj["history_num"]) > 0:
                        fio += ", " + obj["history_num"]
                    tmp.append(Paragraph(fio, styleSheet["BodyText"]))
                    tmp.append(Paragraph(obj["direction"], styleSheet["BodyText"]))
                    tmp.append(Paragraph(obj["tube_id"], styleSheet["BodyText"]))
                    tmp.append(Paragraph(obj["type"], styleSheet["BodyText"]))
                else:
                    tmp.append("")
                    tmp.append("")
                    tmp.append("")
                    tmp.append("")
                    tmp.append("")
                research_tmp = obj["researches"]
                if len(research_tmp) > 44:
                    research_tmp = research_tmp[0:-(len(research_tmp) - 44)] + "..."
                tmp.append(Paragraph(research_tmp, styleSheet["BodyText"]))

                data.append(tmp)
                num += 1

            style = TableStyle([
                ('TEXTCOLOR', (0, -1), (-1, -1), colors.black),
                ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
                ('VALIGN', (0, 0), (-1, -1), "MIDDLE"),
                ('LEFTPADDING', (0, 0), (-1, -1), 1),
                ('RIGHTPADDING', (0, 0), (-1, -1), 1),
                ('TOPPADDING', (0, 0), (-1, -1), 1),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 1)
            ])
            for span in merge_list:  # Цикл объединения ячеек
                for pos in range(0, 6):
                    style.add('INNERGRID', (pos, merge_list[span][0]),
                              (pos, merge_list[span][0] + len(merge_list[span])), 0.28, colors.white)
                    style.add('BOX', (pos, merge_list[span][0]), (pos, merge_list[span][0] + len(merge_list[span])),
                              0.2, colors.black)
            t = Table(data, colWidths=[int(tw * 0.03), int(tw * 0.23), int(tw * 0.09),
                                       int(tw * 0.09), int(tw * 0.23), int(tw * 0.35)],
                      style=style)

            t.canv = c
            wt, ht = t.wrap(0, 0)
            t.drawOn(c, tx, h - ht - ty)
            if pg.has_next():
                c.showPage()

    c.save()

    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)

    group_str = "Все исследования"
    if group >= 0:
        group_str = directory.ResearchGroup.objects.get(pk=group).title
    elif group == -2:
        group_str = "Все исследования"
    else:
        group_str = "Без группы"

    slog.Log(key="", type=25, body=json.dumps({"group": group_str, "start": start}), user=request.user.doctorprofile).save()
    return response


def drawTituls(c, user, pages, page, paddingx, obj, otd="", group=-2):
    """Функция рисования шапки и подвала страницы pdf"""
    c.setFont('OpenSans', 9)
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(1)

    c.drawCentredString(w / 2, h - 30, "Клиники ФГБОУ ВО ИГМУ Минздрава России")
    c.setFont('OpenSans', 12)
    c.drawCentredString(w / 2, h - 50, "Журнал приема материала")
    group_str = "Все исследования"

    if group >= 0:
        group_str = directory.ResearchGroup.objects.get(pk=group).title
    elif group == -2:
        group_str = "Все исследования"
    else:
        group_str = "Без группы"

    c.drawString(paddingx, h - 65, "Группа: %s" % group_str)

    c.drawString(paddingx, h - 78, "Отделение: %s" % otd)

    c.setFont('OpenSans', 10)
    # c.drawString(paddingx * 3, h - 70, "№ " + str(doc_num))
    c.drawRightString(w - paddingx, h - 65,
                      "Дата: " + str(dateformat.format(date.today(), settings.DATE_FORMAT)))

    c.drawRightString(w - paddingx, 20, "Страница " + str(page) + " из " + str(pages))

