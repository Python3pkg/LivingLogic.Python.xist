#! /usr/bin/env python

from xsc_specials import *

class page(XSCElement):
	attr_handlers = { "title" : XSCTextAttr , "head" : XSCTextAttr , "align" : XSCTextAttr , "refresh" : XSCTextAttr , "class" : XSCTextAttr , "keywords" : XSCTextAttr , "description" : XSCTextAttr , "onload" : XSCTextAttr , "nohome" : XSCTextAttr , "nosearch" : XSCTextAttr , "nositemap" : XSCTextAttr , "nofaq" : XSCTextAttr , "notinsitemap" : XSCTextAttr }
	empty = 0

	def asHTML(self):
		t = None
		if self.has_attr("title"):
			t = title(self["title"])
		refresh = None
		if self.has_attr("refresh"):
			refresh = meta(http_equiv="Refresh",content=self["refresh"])
		keywords = None
		if self.has_attr("keywords"):
			keywords = meta(http_equiv="keywords",content=self["keywords"])
		description = None
		if self.has_attr("description"):
			description = meta(http_equiv="description",content=self["description"])
		h = head(
			t+
			link(rel="stylesheet",type="text/css",href=":stylesheets/bnv.css")+
			link(rel="made",href="mailto:html@bnbt.de")+
			refresh+
			keywords+
			description
		)
		b = plainbody(self.content,bgcolor="#fff",text="#000",link="#c63",vlink="#999").asHTML()
		if self.has_attr("class"):
			b["class"] = self["class"]
		if self.has_attr("onload"):
			b["onload"] = self["onload"]
		return XSCDocType('HTML PUBLIC "-//W3C//DTD HTML 4.0 transitional//EN"')+html(h+b)
RegisterElement("page",page)

class blankpage(XSCElement):
	empty = 0
	attr_handlers = { "title" : XSCTextAttr , "notinsitemap" : XSCTextAttr }

	def asHTML(self):
		e = html(
			head(
				title(self["title"])+
				script(type="text/javascript",language="Javascript",src=":javascripts/main.js")+
				link(src="made",href="mailto:html@bnbt.de")
			)+
			plainbody(self.content,bgcolor="white")
		)

		return e.asHTML()
RegisterElement("blankpage",blankpage)

class links(XSCElement):
	empty = 0
RegisterElement("links",links)

class scripts(XSCElement):
	empty = 0
RegisterElement("scripts",scripts)

class indent(XSCElement):
	empty = 1
	
	def asHTML(self):
		return XSCFrag([nbsp()]*4)
RegisterElement("indent",indent)

class _(XSCElement):
	empty = 1
	
	def asHTML(self):
		return " - "
RegisterElement("_",_)

class pfeil(img):
	empty = 1
	attr_handlers = AppendDict(img.attr_handlers,{ "rel" : XSCTextAttr })
	
	def asHTML(self):
		e = img(self.content.asHTML(),self.attrs - [ "rel" ])
		e["border"] = 0
		e["src"] = [":images/links/" , self["rel"] , ".gif" ]

		return e
RegisterElement("pfeil",pfeil)

class capbnv(XSCElement):
	empty = 1
	
	def asHTML(self):
		return cap("Bnv").asHTML()
RegisterElement("capbnv",capbnv)

class capxml(XSCElement):
	empty = 1
	
	def asHTML(self):
		return cap("Xml").asHTML()
RegisterElement("capxml",capxml)

class capcss(XSCElement):
	empty = 1
	
	def asHTML(self):
		return cap("Css").asHTML()
RegisterElement("capcss",capcss)

class capgeo(XSCElement):
	empty = 1
	
	def asHTML(self):
		return cap("Geo").asHTML()
RegisterElement("capgeo",capgeo)

class capcisco(XSCElement):
	empty = 1
	
	def asHTML(self):
		return cap("Cisco").asHTML()
RegisterElement("capcisco",capcisco)

class capsun(XSCElement):
	empty = 1
	
	def asHTML(self):
		return cap("Sun").asHTML()
RegisterElement("capsun",capsun)

class capcgi(XSCElement):
	empty = 1
	
	def asHTML(self):
		return cap("Cgi").asHTML()
RegisterElement("capcgi",capcgi)

class capphp(XSCElement):
	empty = 1
	
	def asHTML(self):
		return cap("Php").asHTML()
RegisterElement("capphp",capphp)

class capbin(XSCElement):
	empty = 1
	
	def asHTML(self):
		return cap("Bin").asHTML()
RegisterElement("capbin",capbin)

class capwww(XSCElement):
	empty = 1
	
	def asHTML(self):
		return cap("www").asHTML()
RegisterElement("capwww",capwww)

class capknf(XSCElement):
	empty = 1
	
	def asHTML(self):
		return cap("Knf").asHTML()
RegisterElement("capknf",capknf)

class caphtml(XSCElement):
	empty = 1
	
	def asHTML(self):
		return cap("Html").asHTML()
RegisterElement("caphtml",caphtml)

class capowinet(XSCElement):
	empty = 1
	
	def asHTML(self):
		return cap("OwiNet").asHTML()
RegisterElement("capowinet",capowinet)

class capmcs(XSCElement):
	empty = 1
	
	def asHTML(self):
		return cap("Mcs").asHTML()
RegisterElement("capmcs",capmcs)

class capcfs(XSCElement):
	empty = 1
	
	def asHTML(self):
		return cap("Cfs").asHTML()
RegisterElement("capcfs",capcfs)

class capdaa(XSCElement):
	empty = 1
	
	def asHTML(self):
		return cap("Daa").asHTML()
RegisterElement("capdaa",capdaa)

class capvhs(XSCElement):
	empty = 1
	
	def asHTML(self):
		return cap("Vhs").asHTML()
RegisterElement("capvhs",capvhs)

class capakzent(XSCElement):
	empty = 1
	
	def asHTML(self):
		return cap("Akzent").asHTML()
RegisterElement("capakzent",capakzent)

class capcvjm(XSCElement):
	empty = 1
	
	def asHTML(self):
		return cap("Cvjm").asHTML()
RegisterElement("capcvjm",capcvjm)

class capccb(XSCElement):
	empty = 1
	
	def asHTML(self):
		return cap("Ccb").asHTML()
RegisterElement("capccb",capccb)

class capppp(XSCElement):
	empty = 1
	
	def asHTML(self):
		return cap("ppp").asHTML()
RegisterElement("capppp",capppp)

class capmtla(XSCElement):
	empty = 1
	
	def asHTML(self):
		return cap("Mtla").asHTML()
RegisterElement("capmtla",capmtla)

class capbfs(XSCElement):
	empty = 1
	
	def asHTML(self):
		return cap("Bfs").asHTML()
RegisterElement("capbfs",capbfs)

class capihk(XSCElement):
	empty = 1
	
	def asHTML(self):
		return cap("Ihk").asHTML()
RegisterElement("capihk",capihk)

class capdag(XSCElement):
	empty = 1
	
	def asHTML(self):
		return cap("Dag").asHTML()
RegisterElement("capdag",capdag)

class capvwa(XSCElement):
	empty = 1
	
	def asHTML(self):
		return cap("Vwa").asHTML()
RegisterElement("capvwa",capvwa)

class capbfz(XSCElement):
	empty = 1
	
	def asHTML(self):
		return cap("Bfz").asHTML()
RegisterElement("capbfz",capbfz)

class capedv(XSCElement):
	empty = 1
	
	def asHTML(self):
		return cap("edv").asHTML()
RegisterElement("capedv",capedv)

class capbitoek(XSCElement):
	empty = 1
	
	def asHTML(self):
		return cap("Bit�k").asHTML()
RegisterElement("capbitoek",capbitoek)

class capdfn(XSCElement):
	empty = 1
	
	def asHTML(self):
		return cap("Dfn").asHTML()
RegisterElement("capdfn",capdfn)

class capizb(XSCElement):
	empty = 1
	
	def asHTML(self):
		return cap("Izb").asHTML()
RegisterElement("capizb",capizb)

class capdat(XSCElement):
	empty = 1
	
	def asHTML(self):
		return cap("Dat").asHTML()
RegisterElement("capdat",capdat)

class capdns(XSCElement):
	empty = 1
	
	def asHTML(self):
		return cap("Dns").asHTML()
RegisterElement("capdns",capdns)

class capascend(XSCElement):
	empty = 1
	
	def asHTML(self):
		return cap("Ascend").asHTML()
RegisterElement("capascend",capascend)

class capmax(XSCElement):
	empty = 1
	
	def asHTML(self):
		return cap("Max").asHTML()
RegisterElement("capmax",capmax)

class capisdn(XSCElement):
	empty = 1
	
	def asHTML(self):
		return cap("Isdn").asHTML()
RegisterElement("capisdn",capisdn)

class cappdf(XSCElement):
	empty = 1
	
	def asHTML(self):
		return cap("Pdf").asHTML()
RegisterElement("cappdf",cappdf)

class capiso(XSCElement):
	empty = 1
	
	def asHTML(self):
		return cap("Iso").asHTML()
RegisterElement("capiso",capiso)

class capurl(XSCElement):
	empty = 1
	
	def asHTML(self):
		return cap("Url").asHTML()
RegisterElement("capurl",capurl)

class caphttp(XSCElement):
	empty = 1
	
	def asHTML(self):
		return cap("Http").asHTML()
RegisterElement("caphttp",caphttp)

class capsmtp(XSCElement):
	empty = 1
	
	def asHTML(self):
		return cap("Smtp").asHTML()
RegisterElement("capsmtp",capsmtp)

class capftp(XSCElement):
	empty = 1
	
	def asHTML(self):
		return cap("ftp").asHTML()
RegisterElement("capftp",capftp)

class cappop3(XSCElement):
	empty = 1
	
	def asHTML(self):
		return cap("Pop3").asHTML()
RegisterElement("cappop3",cappop3)

class capcvs(XSCElement):
	empty = 1
	
	def asHTML(self):
		return cap("Cvs").asHTML()
RegisterElement("capcvs",capcvs)

class capfaq(XSCElement):
	empty = 1
	
	def asHTML(self):
		return cap("Faq").asHTML()
RegisterElement("capfaq",capfaq)

class capgnu(XSCElement):
	empty = 1
	
	def asHTML(self):
		return cap("Gnu").asHTML()
RegisterElement("capgnu",capgnu)

class caphsc(XSCElement):
	empty = 1
	
	def asHTML(self):
		return cap("Hsc").asHTML()
RegisterElement("caphsc",caphsc)

class capunix(XSCElement):
	empty = 1
	
	def asHTML(self):
		return cap("Unix").asHTML()
RegisterElement("capunix",capunix)

class par(div):
	empty = 0
	attr_handlers = AppendDict(div.attr_handlers,{ "noindent" : XSCTextAttr })
	
	def asHTML(self):
		e = div(self.content.asHTML(),(self.attrs - "noindent").asHTML())
		if not self.has_attr("noindent"):
			e["class"] = "indent"
		return e
RegisterElement("par",par)

class blob(XSCElement):
	empty = 1
	
	def asHTML(self):
		return (nbsp() + "- ").asHTML()
RegisterElement("blob",blob)

class schulen(dl):
	empty = 0

	def asHTML(self):
		return dl(self.content.asHTML(),self.attrs.asHTML())
RegisterElement("schulen",schulen)

class schule(XSCElement):
	empty = 0
	attr_handlers = { "privat" : XSCTextAttr , "art" : XSCTextAttr , "anschrift" : XSCTextAttr , "telefon" : XSCTextAttr , "url" : XSCURLAttr }
	
	def asHTML(self):
		t = XSCFrag()
		if self.has_attr("url"):
			t = t + a(b(self.content.asHTML()),href=self["url"])
		else:
			t = t + b(self.content.asHTML())
		if self.has_attr("privat"):
			t = t + " (Privat)"
		d = XSCFrag()
		if self.has_attr("art"):
			d = d + [ self["art"] , "; " ]
		if self.has_attr("anschrift"):
			d = d + [ self["anschrift"] , "; " ]
		if self.has_attr("telefon"):
			d = d + [ "Tel.: " , self["telefon"] ]
		d = div(Class="schule-text")
		return dt(t) + dd(div(d))
RegisterElement("schule",schule)

class fileinfo(XSCElement):
	empty = 1

	def asHTML(self):
		e = tr(
			td(indent(),rowspan=3) +
			td(div(pfeil(rel="info") + nbsp(),Class="lnk-title"),nowrap="") +
			td(div("Letzte �nderung",Class="lnk-title"),nowrap="") +
			td(indent())
		)+tr(
			td(pixel()) +
			td(pixel(),colspan=2,bgcolor="#fff")
		)+tr(
			td(pixel())+
			td(div("Now" + br() + a(href="mailto:webmaster@bnbt.de"),Class="lnk-text"),nowrap="")
		)+tr(
			td(pixel(height=10))
		)+tr(
			td(pixel(),colspan=4)
		)

		return e.asHTML()
RegisterElement("fileinfo",fileinfo)

class navigation(XSCElement):
	empty = 1
	attr_handlers = { "off" : XSCTextAttr , "href" : XSCURLAttr , "img" : XSCTextAttr , "text" : XSCTextAttr }

	def asHTML(self):
		td1 = td([nbsp()]*3,Class="links",bgcolor="#333366")
		td2 = td(span("",Class="biglink"),Class="links",bgcolor="#333366",valign="middle",align="center")
		e = XSCFrag(td1+td2)

		return e.asHTML()
RegisterElement("navigation",navigation)

class content(XSCElement):
	attr_handlers = { "align" : XSCTextAttr }
	empty = 0
RegisterElement("content",content)

class bytes(XSCElement):
	attr_handlers = { "file" : XSCURLAttr }
	empty = 1
RegisterElement("bytes",bytes)

class hrf(XSCElement):
	attr_handlers = { "rel" : XSCTextAttr , "href" : XSCURLAttr , "off" : XSCTextAttr , "class" : XSCTextAttr , "target" : XSCTextAttr }
	empty = 0
RegisterElement("hrf",hrf)

class lnk(XSCElement):
	attr_handlers = { "rel" : XSCTextAttr , "href" : XSCURLAttr , "text" : XSCTextAttr }
	empty = 0
RegisterElement("lnk",lnk)

class vorstand(XSCElement):
	attr_handlers = { "name" : XSCTextAttr , "posten" : XSCTextAttr , "email" : XSCTextAttr , "homepage" : XSCTextAttr }
	empty = 1
RegisterElement("vorstand",vorstand)

class firmen(XSCElement):
	empty = 0
RegisterElement("firmen",firmen)	

class firma(XSCElement):
	attr_handlers = { "anschrift" : XSCTextAttr , "telefon" : XSCTextAttr ,  "url" : XSCURLAttr }
	empty = 0
RegisterElement("firma",firma)	

class kirchen(XSCElement):
	empty = 0
RegisterElement("kirchen",kirchen)	

class kirche(XSCElement):
	attr_handlers = { "ansprech" : XSCTextAttr , "strasse" : XSCTextAttr ,  "ort" : XSCURLAttr , "telefon" : XSCTextAttr , "url" : XSCURLAttr , "dekanat" : XSCTextAttr }
	empty = 0
RegisterElement("kirche",kirche)	

class above(XSCElement):
	atts_handlers = { "rel" : XSCTextAttr , "href" : XSCTextAttr , "class" : XSCTextAttr }
	empty = 0
RegisterElement("above",above)

class shell(XSCElement):
	empty = 0
RegisterElement("shell",shell)

class faq(XSCElement):
	attr_handlers = { "frage" : XSCTextAttr }
	empty = 0
RegisterElement("faq",faq)

class engines(XSCElement):
	empty = 0

	def asHTML(self):
		e = dl(self.content)
		return e.asHTML()
RegisterElement("engines",engines)

class engine(XSCElement):
	empty = 0
	attr_handlers = { "name" : XSCTextAttr , "url" : XSCURLAttr }

	def asHTML(self):
		e = XSCFrag(
			dt(b(self["name"]) + " (" + hrf(self["url"],href=self["url"]) + ")")+
			dd(div(self.content,Class="engine-text"))
		)

		return e.asHTML()

RegisterElement("engine",engine)

class bnvereine(XSCElement):
	empty = 0

	def asHTML(self):
		e = dl(self.content)
		return e.asHTML()
RegisterElement("bnvereine",bnvereine)

class bnverein(XSCElement):
	empty = 0
	attr_handlers = { "name" : XSCTextAttr , "url" : XSCURLAttr }

	def asHTML(self):
		e = XSCFrag(
			dt(b(self["name"]) + " (" + hrf(self["url"],href=self["url"]) + ")")+
			dd(div(self.content,Class="bnverein-text"))
		)

		return e.asHTML()

RegisterElement("bnverein",bnverein)

class fahrplansite(XSCElement):
	empty = 0
	attr_handlers = { "name" : XSCTextAttr , "url" : XSCURLAttr }

	def asHTML(self):
		e = XSCFrag(
			dt(b(self["name"]) + " (" + hrf(self["url"],href=self["url"]) + ")")+
			dd(div(self.content,Class="fahrplan-text"))
		)

		return e.asHTML()
RegisterElement("fahrplansite",fahrplansite)

class fahrplansites(XSCElement):
	empty = 0

	def asHTML(self):
		e = dl(self.content)

		return e.asHTML()
RegisterElement("fahrplansites",fahrplansites)

class fahrplan(XSCElement):
	empty = 0
	attr_handlers = { "name" : XSCTextAttr , "url" : XSCURLAttr }

	def asHTML(self):
		halts = self.findElementsNamed("haltestelle")
		flipflop = "even"
		for halt in halts:
			halt["class"] = flipflop
			if flipflop == "even":
				flipflop = "odd"
			else:
				flipflop = "even"
		e = plaintable(halts,Class="fahrplan",cellpadding="2",cellspacing="1")

		return e.asHTML()
RegisterElement("fahrplan",fahrplan)

class halt(XSCElement):
	empty = 0

	def asHTML(self):
		e = td(self.content,align="right",Class="halt")

		return e.asHTML()
RegisterElement("halt",halt)


class keinhalt(XSCElement):
	empty = 1

	def asHTML(self):
		e = td()

		return e.asHTML()
RegisterElement("keinhalt",keinhalt)

class haltestelle(XSCElement):
	empty = 0
	attr_handlers = { "name" : XSCTextAttr , "an" : XSCTextAttr , "class" : XSCTextAttr }

	def asHTML(self):
		if self.has_attr("an"):
			anab = td("an")
		else:
			anab = td("ab")
		e = tr(
			th(self["name"],Class="left")+
			anab+
			self.content+
			anab+
			th(self["name"],Class="right")
		)
		if self.has_attr("class"):
			e["class"] = self["class"]

		return e.asHTML()
RegisterElement("haltestelle",haltestelle)

class downloadsites(XSCElement):
	empty = 0
RegisterElement("downloadsites",downloadsites)

class downloadsite(XSCElement):
	attr_handlers = { "name" : XSCTextAttr , "url" : XSCURLAttr }
	empty = 0
RegisterElement("downloadsite",downloadsite)

class newstickers(XSCElement):
	empty = 0

	def asHTML(self):
		e = dl(self.content)

		return e.asHTML()
RegisterElement("newstickers",newstickers)

class newsticker(XSCElement):
	empty = 0
	attr_handlers = { "name" : XSCTextAttr , "url" : XSCURLAttr }

	def asHTML(self):
		e = XSCFrag(
			dt(b(self["name"]) + " (" + hrf(self["url"],href=self["url"]) + ")")+
			dd(div(self.content,Class="newsticker-text"))
		)

		return e.asHTML()

RegisterElement("newsticker",newsticker)

class kleinanzeige(XSCElement):
	attr_handlers = { "bezeichnung" : XSCTextAttr , "preis" : XSCTextAttr , "tel" : XSCTextAttr , "email" : XSCTextAttr , "handy" : XSCTextAttr , "fax" : XSCTextAttr }
	empty = 0
RegisterElement("kleinanzeige",kleinanzeige)

class kleinanzeige_handy(XSCElement):
	empty = 0
RegisterElement("kleinanzeige-handy",kleinanzeige_handy)


class kleinanzeige_fax(XSCElement):
	empty = 0
RegisterElement("kleinanzeige-fax",kleinanzeige_fax)

class newsitems(XSCElement):
	empty = 0

	def asHTML(self):
		e = plaintable(self.content,Class="newsitems")

		return e.asHTML()
RegisterElement("newsitems",newsitems)

class newsitem(XSCElement):
	attr_handlers = { "datum" : XSCTextAttr , "href" : XSCTextAttr }
	empty = 0

	def asHTML(self):
		e = tr(
			td(b(self["datum"]+nbsp()),valign="top")+
			td(a(self.content,href=":aktuelles/"+self["href"]+".html"))
		,Class="newsitem")

		return e.asHTML()
RegisterElement("newsitem",newsitem)

class pagenewsitem(XSCElement):
	empty = 0
	attr_handlers = { "datum" : XSCTextAttr }

	def asHTML(self):
		e = page(links()+content(self.content),title="B�rgernetz Bayreuth - Aktuelles - "+self["datum"],keywords="B�rgernetz, Bayreuth, Aktuelles")

		return e.asHTML()
RegisterElement("pagenewsitem",pagenewsitem)

class zonk(XSCElement):
	empty = 0

	def asHTML(self):
		return XSCdiv(self.content.asHTML(),Class="zonk")
RegisterElement("zonk",zonk)

class buergerfestbild(XSCElement):
	empty = 0
	attr_handlers = { "src" : XSCTextAttr }

	def asHTML(self):
		e = plaintable(
			tr(
				td(
					a(
						img(src=":trv/buergerfest1999/images/pic" + self["src"] + "-thumb.jpg",border="0"),
						href=":trv/buergerfest1999/images/pic" + self["src"] + ".jpg"
					)
				)
			),cellpadding="1",bgcolor="#000"
		)
		return e.asHTML()
RegisterElement("buergerfestbild",buergerfestbild)

if __name__ == "__main__":
	print str(xsc.parseFile(sys.argv[1]).asHTML())

