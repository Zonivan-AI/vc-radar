#!/usr/bin/env python3
"""
expand_vc_list.py — Expand VC Radar's vc_list.yaml to 1000+ firms.

Strategy:
  1. Load existing VCs from config/vc_list.yaml
  2. Scrape free VC directories (Wikipedia, DuckDuckGo searches) for new firms
  3. Auto-discover portfolio page URLs for VCs that have a website but no portfolio_url
  4. Merge everything and write an updated vc_list.yaml

Usage:
    python scripts/expand_vc_list.py [--dry-run] [--skip-discovery] [--skip-scrape]
"""

import argparse
import asyncio
import logging
import os
import random
import re
import sys
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

import aiohttp
import yaml
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VC_LIST_PATH = PROJECT_ROOT / "config" / "vc_list.yaml"
OUTPUT_PATH = PROJECT_ROOT / "config" / "vc_list.yaml"
BACKUP_PATH = PROJECT_ROOT / "config" / "vc_list.yaml.bak"

RATE_LIMIT_SECS = 1.5  # seconds between requests (polite crawling)
MAX_CONCURRENT = 5      # max parallel connections for portfolio discovery
REQUEST_TIMEOUT = 12    # seconds

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# Common portfolio page paths to probe
PORTFOLIO_PATHS = [
    "/portfolio",
    "/portfolio/",
    "/companies",
    "/companies/",
    "/investments",
    "/investments/",
    "/our-companies",
    "/our-companies/",
    "/portfolio-companies",
    "/portfolio-companies/",
    "/startups",
    "/startups/",
    "/our-portfolio",
    "/our-portfolio/",
    "/backed",
    "/backed/",
    "/our-investments",
    "/our-investments/",
    "/work",
    "/work/",
]

# DuckDuckGo search queries to discover VC firms
DDG_QUERIES = [
    "top venture capital firms list 2024",
    "best VC firms in silicon valley list",
    "top seed stage venture capital firms",
    "series A venture capital firms list",
    "european venture capital firms list",
    "top VC firms fintech AI list",
    "venture capital firm directory 2024",
    "emerging venture capital firms list",
    "top growth equity firms list",
    "best early stage VC firms",
    "top venture capital firms healthcare biotech",
    "asia venture capital firms list",
    "top crypto web3 venture capital firms",
    "climate tech venture capital firms",
    "top enterprise software VC firms",
    "new york venture capital firms list",
    "london venture capital firms list",
    "top micro VC firms list",
    "venture capital firms india list",
    "top deep tech venture capital firms",
]

# Well-known VC firms to seed if not already in list (name, website)
SEED_VCS = [
    ("Sequoia Capital", "https://www.sequoiacap.com"),
    ("Andreessen Horowitz", "https://a16z.com"),
    ("Kleiner Perkins", "https://www.kleinerperkins.com"),
    ("Benchmark", "https://www.benchmark.com"),
    ("Greylock Partners", "https://greylock.com"),
    ("Lightspeed Venture Partners", "https://lsvp.com"),
    ("Bessemer Venture Partners", "https://www.bvp.com"),
    ("General Catalyst", "https://www.generalcatalyst.com"),
    ("Index Ventures", "https://www.indexventures.com"),
    ("Founders Fund", "https://foundersfund.com"),
    ("NEA", "https://www.nea.com"),
    ("Khosla Ventures", "https://www.khoslaventures.com"),
    ("Battery Ventures", "https://www.battery.com"),
    ("Insight Partners", "https://www.insightpartners.com"),
    ("Tiger Global Management", "https://www.tigerglobal.com"),
    ("Coatue Management", "https://www.coatue.com"),
    ("Ribbit Capital", "https://ribbitcap.com"),
    ("Thrive Capital", "https://www.thrivecap.com"),
    ("Addition", "https://www.addition.com"),
    ("Spark Capital", "https://www.sparkcapital.com"),
    ("Union Square Ventures", "https://www.usv.com"),
    ("Accel", "https://www.accel.com"),
    ("GV", "https://www.gv.com"),
    ("IVP", "https://www.ivp.com"),
    ("Menlo Ventures", "https://www.menlovc.com"),
    ("Redpoint Ventures", "https://www.redpoint.com"),
    ("Sapphire Ventures", "https://sapphireventures.com"),
    ("Scale Venture Partners", "https://www.scalevp.com"),
    ("Canaan Partners", "https://www.canaan.com"),
    ("Felicis Ventures", "https://www.felicis.com"),
    ("First Round Capital", "https://firstround.com"),
    ("Flybridge", "https://www.flybridge.com"),
    ("Forerunner Ventures", "https://www.forerunnerventures.com"),
    ("Foundation Capital", "https://www.foundationcap.com"),
    ("Freestyle Capital", "https://freestyle.vc"),
    ("Gradient Ventures", "https://www.gradient.com"),
    ("Greycroft", "https://www.greycroft.com"),
    ("Homebrew", "https://homebrew.co"),
    ("Innovation Endeavors", "https://www.innovationendeavors.com"),
    ("Initialized Capital", "https://initialized.com"),
    ("Lerer Hippeau", "https://www.lererhippeau.com"),
    ("Lowercase Capital", "https://lowercasecapital.com"),
    ("Matrix Partners", "https://www.matrixpartners.com"),
    ("Maverick Ventures", "https://www.maverickventures.com"),
    ("Mayfield", "https://www.mayfield.com"),
    ("Norwest Venture Partners", "https://www.nvp.com"),
    ("Obvious Ventures", "https://obvious.com"),
    ("Pelion Venture Partners", "https://www.pelionvp.com"),
    ("Polaris Partners", "https://www.polarispartners.com"),
    ("QED Investors", "https://www.qedinvestors.com"),
    ("Quiet Capital", "https://www.quiet.com"),
    ("RRE Ventures", "https://rre.com"),
    ("Sutter Hill Ventures", "https://www.shv.com"),
    ("SV Angel", "https://www.svangel.com"),
    ("True Ventures", "https://trueventures.com"),
    ("Two Sigma Ventures", "https://www.twosigmaventures.com"),
    ("Upfront Ventures", "https://upfront.com"),
    ("Venrock", "https://www.venrock.com"),
    ("Versant Ventures", "https://www.versantventures.com"),
    ("Wing Venture Capital", "https://www.wing.vc"),
    ("Y Combinator", "https://www.ycombinator.com"),
    ("Atomico", "https://www.atomico.com"),
    ("Balderton Capital", "https://www.balderton.com"),
    ("Cherry Ventures", "https://www.cherry.vc"),
    ("Creandum", "https://www.creandum.com"),
    ("Dawn Capital", "https://www.dawncapital.com"),
    ("EQT Ventures", "https://eqtventures.com"),
    ("Felix Capital", "https://www.felixcapital.com"),
    ("HV Capital", "https://www.hvcapital.com"),
    ("Lakestar", "https://www.lakestar.com"),
    ("LocalGlobe", "https://localglobe.vc"),
    ("Mosaic Ventures", "https://www.mosaicventures.com"),
    ("Notion Capital", "https://www.notioncapital.com"),
    ("Northzone", "https://www.northzone.com"),
    ("Point Nine Capital", "https://www.pointnine.com"),
    ("Seedcamp", "https://www.seedcamp.com"),
    ("Speedinvest", "https://www.speedinvest.com"),
    ("Stride.VC", "https://www.stride.vc"),
    ("Valar Ventures", "https://www.valarventures.com"),
    ("Acacia Partners", "https://www.acaciapartners.com"),
    ("Amplify Partners", "https://www.amplifypartners.com"),
    ("Aspect Ventures", "https://www.aspectventures.com"),
    ("B Capital Group", "https://www.bcapgroup.com"),
    ("Bain Capital Ventures", "https://www.baincapitalventures.com"),
    ("Base10 Partners", "https://base10.vc"),
    ("Bedrock Capital", "https://www.bedrockcap.com"),
    ("Bowery Capital", "https://bowerycap.com"),
    ("BoxGroup", "https://www.boxgroup.com"),
    ("Breakthrough Energy Ventures", "https://www.breakthroughenergy.org"),
    ("Caffeinated Capital", "https://www.caffeinatedcapital.com"),
    ("ClearVue Partners", "https://www.clearvuepartners.com"),
    ("Costanoa Ventures", "https://www.costanoavc.com"),
    ("CRV", "https://www.crv.com"),
    ("Decibel Partners", "https://decibel.vc"),
    ("Drive Capital", "https://www.drivecapital.com"),
    ("Dragoneer Investment Group", "https://www.dragoneer.com"),
    ("Elad Gil", "https://eladgil.com"),
    ("Elephant", "https://www.elephantvc.com"),
    ("Emergence Capital", "https://www.emcap.com"),
    ("Eniac Ventures", "https://www.eniac.vc"),
    ("Entree Capital", "https://www.entreecapital.com"),
    ("Craft Ventures", "https://www.craftventures.com"),
    ("Correlation Ventures", "https://www.correlationvc.com"),
    ("Data Collective (DCVC)", "https://www.dcvc.com"),
    ("Floodgate", "https://www.floodgate.com"),
    ("Glade Brook Capital", "https://www.gladebrookcapital.com"),
    ("G Squared", "https://gsquared.com"),
    ("General Atlantic", "https://www.generalatlantic.com"),
    ("Georgian", "https://georgian.io"),
    ("Global Founders Capital", "https://www.globalfounderscapital.com"),
    ("GGV Capital", "https://www.ggvc.com"),
    ("Goldman Sachs Growth", "https://www.gs.com"),
    ("Goodwater Capital", "https://www.goodwatercap.com"),
    ("Greenoaks Capital", "https://www.greenoakscap.com"),
    ("Headline", "https://www.headline.com"),
    ("High Alpha", "https://www.highalpha.com"),
    ("Iconiq Capital", "https://www.iconiqcapital.com"),
    ("Intel Capital", "https://www.intelcapital.com"),
    ("Jungle Ventures", "https://www.jungle-ventures.com"),
    ("K9 Ventures", "https://www.k9ventures.com"),
    ("Kindred Ventures", "https://www.kindredventures.com"),
    ("Lux Capital", "https://www.luxcapital.com"),
    ("M13", "https://m13.co"),
    ("March Capital", "https://www.marchcp.com"),
    ("Meritech Capital", "https://www.meritechcapital.com"),
    ("Mubadala Ventures", "https://www.mubadala.com"),
    ("Nautilus Venture Partners", "https://www.nautilusvp.com"),
    ("Next47", "https://next47.com"),
    ("Omega Venture Partners", "https://www.omegavp.com"),
    ("Openview Partners", "https://openviewpartners.com"),
    ("Pear VC", "https://www.pear.vc"),
    ("Playground Global", "https://playground.global"),
    ("Primary Venture Partners", "https://www.primaryvc.com"),
    ("Radical Ventures", "https://www.radical.vc"),
    ("Reach Capital", "https://www.reachcapital.com"),
    ("Ridge Ventures", "https://www.ridgevc.com"),
    ("Salesforce Ventures", "https://www.salesforceventures.com"),
    ("Samsung NEXT", "https://www.samsungnext.com"),
    ("Shasta Ventures", "https://www.shastaventures.com"),
    ("SignalFire", "https://www.signalfire.com"),
    ("Social Capital", "https://www.socialcapital.com"),
    ("Soma Capital", "https://www.somacap.com"),
    ("South Park Commons", "https://www.southparkcommons.com"),
    ("SoftBank Vision Fund", "https://visionfund.com"),
    ("Storm Ventures", "https://www.stormventures.com"),
    ("Stripes", "https://www.stripes.co"),
    ("Susquehanna Growth Equity", "https://www.sgep.com"),
    ("Tao Capital Partners", "https://www.taocap.com"),
    ("TCV", "https://www.tcv.com"),
    ("Tencent Investment", "https://www.tencent.com"),
    ("Thomvest Ventures", "https://www.thomvest.com"),
    ("Trinity Ventures", "https://www.trinityventures.com"),
    ("Verizon Ventures", "https://www.verizon.com/about/ventures"),
    ("Village Global", "https://www.villageglobal.vc"),
    ("Volition Capital", "https://www.volitioncapital.com"),
    ("WndrCo", "https://www.wndrco.com"),
    ("Workbench", "https://www.workbench.vc"),
    ("Zetta Venture Partners", "https://www.zettavp.com"),
    ("Zigg Capital", "https://www.ziggcap.com"),
    ("01 Advisors", "https://www.01advisors.com"),
    ("a]ventures", "https://www.a.ventures"),
    ("Abstract Ventures", "https://www.abstractvc.com"),
    ("Accomplice", "https://www.accomplice.co"),
    ("Aisling Capital", "https://www.aislingcapital.com"),
    ("Alumni Ventures", "https://www.av.vc"),
    ("Anthos Capital", "https://www.anthoscapital.com"),
    ("Avenir Growth Capital", "https://www.avenirgrowth.com"),
    ("Avid Ventures", "https://www.avidventures.com"),
    ("Blossom Street Ventures", "https://www.blossomstreetventures.com"),
    ("Boldstart Ventures", "https://boldstart.vc"),
    ("Brand Foundry Ventures", "https://www.brandfoundry.com"),
    ("Bullpen Capital", "https://www.bullpencap.com"),
    ("Cambium Capital", "https://www.cambiumcap.com"),
    ("Causefolio", "https://www.causefolio.com"),
    ("Cervin Ventures", "https://www.cervin.com"),
    ("Chapter One", "https://www.chapterone.com"),
    ("Clocktower Technology Ventures", "https://www.clocktowertech.com"),
    ("Cloud Apps Capital Partners", "https://www.cloudappscapital.com"),
    ("Comcast Ventures", "https://www.comcastventures.com"),
    ("Contour Venture Partners", "https://www.contourventures.com"),
    ("Conversion Capital", "https://www.conversioncapital.com"),
    ("Cross Creek Advisors", "https://www.crosscreekadvisors.com"),
    ("Crosslink Capital", "https://www.crosslinkcapital.com"),
    ("D1 Capital Partners", "https://www.d1cap.com"),
    ("Defy Partners", "https://defy.vc"),
    ("Delta-v Capital", "https://www.deltav.vc"),
    ("Draper Associates", "https://www.draperassociates.com"),
    ("Draper Fisher Jurvetson", "https://www.dfj.com"),
    ("EarlyBirdVC", "https://www.earlybird.com"),
    ("Eight Roads Ventures", "https://eightroads.com"),
    ("Elaia Partners", "https://www.elaia.com"),
    ("Elevation Capital", "https://www.elevationcapital.com"),
    ("Ember Capital", "https://www.embercapital.com"),
    ("Endeavor Catalyst", "https://endeavorcatalyst.org"),
    ("Engel Capital", "https://www.engelcapital.com"),
    ("Eurazeo", "https://www.eurazeo.com"),
    ("F-Prime Capital", "https://www.fprimecapital.com"),
    ("Fifth Wall", "https://fifthwall.com"),
    ("Fin Capital", "https://www.fincapital.com"),
    ("Firstmark Capital", "https://firstmarkcap.com"),
    ("Footwork", "https://www.footwork.vc"),
    ("Foresite Capital", "https://www.foresitecapital.com"),
    ("Forum Ventures", "https://www.forumvc.com"),
    ("Franklin Templeton", "https://www.franklintempleton.com"),
    ("Frog Capital", "https://frogcapital.com"),
    ("FTV Capital", "https://www.ftvcapital.com"),
    ("Fuel Capital", "https://www.fuelcapital.com"),
    ("Future Ventures", "https://future.com"),
    ("Global Brain", "https://globalbrains.com"),
    ("GreenSky Capital", "https://www.greenskycapital.com"),
    ("Greenspring Associates", "https://greenspringassociates.com"),
    ("Grotech Ventures", "https://www.grotech.com"),
    ("Harlem Capital", "https://www.harlemcapital.com"),
    ("Haystack", "https://haystack.vc"),
    ("Heavybit", "https://www.heavybit.com"),
    ("Heroic Ventures", "https://www.heroicvc.com"),
    ("Human Capital", "https://www.humancapital.vc"),
    ("I2BF Global Ventures", "https://www.i2bf.com"),
    ("Impact America Fund", "https://www.impactamericafund.com"),
    ("Incisive Ventures", "https://www.incisive.vc"),
    ("Industry Ventures", "https://www.industryventures.com"),
    ("Inovia Capital", "https://inovia.vc"),
    ("Intersect Capital", "https://www.intersect.capital"),
    ("J.P. Morgan Growth Equity", "https://www.jpmorgan.com"),
    ("Jackson Square Ventures", "https://www.jsv.com"),
    ("Jump Capital", "https://jumpcap.com"),
    ("Kapor Capital", "https://www.kaporcapital.com"),
    ("Keen Venture Partners", "https://www.keenventurepartners.com"),
    ("Kima Ventures", "https://www.kimaventures.com"),
    ("KKR", "https://www.kkr.com"),
    ("Knollwood Advisory Group", "https://knollwood.com"),
    ("Lachy Groom", "https://www.lachygroom.com"),
    ("Lantern Ventures", "https://www.lanternvc.com"),
    ("Latitude Ventures", "https://www.latitudeventures.com"),
    ("Lead Edge Capital", "https://www.leadedgecapital.com"),
    ("Lemnos", "https://lemnos.vc"),
    ("Liberty Global Ventures", "https://www.libertyglobal.com"),
    ("Lightbank", "https://www.lightbank.com"),
    ("Liquid 2 Ventures", "https://www.liquid2.vc"),
    ("Longtail Ventures", "https://www.longtail.vc"),
    ("MaC Venture Capital", "https://www.macventurecapital.com"),
    ("Madrona Ventures", "https://www.madrona.com"),
    ("Mango Capital", "https://www.mangocap.com"),
    ("Matchstick Ventures", "https://www.matchstickventures.com"),
    ("Maveron", "https://www.maveron.com"),
    ("Meridian Street Capital", "https://www.meridianstreetcapital.com"),
    ("MHS Capital", "https://www.mhscapital.com"),
    ("Millennium Technology Value Partners", "https://www.mtvp.com"),
    ("Morado Ventures", "https://www.moradoventures.com"),
    ("Motley Fool Ventures", "https://www.motleyfoolventures.com"),
    ("MSD Partners", "https://www.msdpartners.com"),
    ("Mucker Capital", "https://www.muckercapital.com"),
    ("New Enterprise Associates", "https://www.nea.com"),
    ("New Stack Ventures", "https://www.newstack.vc"),
    ("NextView Ventures", "https://nextviewventures.com"),
    ("NfX", "https://www.nfx.com"),
    ("Notation Capital", "https://www.notationcapital.com"),
    ("OMERS Ventures", "https://www.omersventures.com"),
    ("Operator Partners", "https://www.operatorpartners.com"),
    ("Optum Ventures", "https://www.optumventures.com"),
    ("Owl Ventures", "https://www.owlvc.com"),
    ("Oxford Science Enterprises", "https://www.oxfordscienceenterprises.com"),
    ("Paladin Capital Group", "https://www.paladincapgroup.com"),
    ("Panorama Point Partners", "https://panoramapoint.com"),
    ("Parafi Capital", "https://www.parafi.com"),
    ("Partech", "https://www.partechpartners.com"),
    ("Paua Ventures", "https://www.pauaventures.com"),
    ("Peak XV Partners", "https://www.peakxv.com"),
    ("Penny Jar Capital", "https://www.pennyjarcapital.com"),
    ("Peterson Ventures", "https://www.petersonventures.com"),
    ("Pillar VC", "https://www.pillarvc.com"),
    ("Pivot North Capital", "https://pivotnorth.com"),
    ("Playground Ventures", "https://playground.vc"),
    ("Precept", "https://precept.vc"),
    ("Prelude Ventures", "https://www.preludeventures.com"),
    ("Propel Venture Partners", "https://www.propelvc.com"),
    ("Propulsion Capital", "https://www.propulsion.vc"),
    ("Prosus Ventures", "https://www.prosus.com"),
    ("Race Capital", "https://www.race.capital"),
    ("Rally Ventures", "https://www.rallyventures.com"),
    ("Rapha Capital", "https://www.rapha.vc"),
    ("Renegade Partners", "https://www.renegade.vc"),
    ("Revolution", "https://www.revolution.com"),
    ("Ribbit Capital", "https://ribbitcap.com"),
    ("RiverPark Ventures", "https://www.riverparkventures.com"),
    ("Root Ventures", "https://www.rootvc.com"),
    ("RTP Global", "https://www.rtpglobal.com"),
    ("Runway Growth Capital", "https://runwaygrowth.com"),
    ("S28 Capital", "https://www.s28capital.com"),
    ("Samsara Capital", "https://www.samsaracapital.com"),
    ("Sands Capital Ventures", "https://www.sandscapital.com"),
    ("Saturn Partners", "https://www.saturnpartners.com"),
    ("Scribble Ventures", "https://www.scribbleventures.com"),
    ("Seven Seven Six", "https://776.org"),
    ("Sherpa Capital", "https://www.sherpacapital.com"),
    ("Sievert Larsen", "https://www.sievertlarsen.com"),
    ("Sierra Ventures", "https://www.sierraventures.com"),
    ("Silicon Valley Bank Capital", "https://www.svb.com"),
    ("Softbank Latin America Fund", "https://www.softbank.com"),
    ("Sorenson Ventures", "https://www.sorensonventures.com"),
    ("Spark Growth Ventures", "https://sparkgrowth.vc"),
    ("Spectrum Equity", "https://www.spectrumequity.com"),
    ("Spruce Capital Partners", "https://www.spruce.vc"),
    ("Stageone Ventures", "https://www.stageoneventures.com"),
    ("Standard Investments", "https://www.standard.com"),
    ("Steadfast Venture Capital", "https://www.steadfastvc.com"),
    ("Struck Capital", "https://www.struckcapital.com"),
    ("Summit Partners", "https://www.summitpartners.com"),
    ("Sunstone Capital", "https://www.sunstone.eu"),
    ("SWaN & Legend Venture Partners", "https://www.swanlegend.com"),
    ("Sway Ventures", "https://swayventures.com"),
    ("Tekton Ventures", "https://www.tektonventures.com"),
    ("Telos Ventures", "https://www.telosventures.com"),
    ("Third Point Ventures", "https://www.thirdpointventures.com"),
    ("Threshold Ventures", "https://www.thresholdvc.com"),
    ("TI Platform Management", "https://www.tiplatform.com"),
    ("Tomorrow Ventures", "https://www.tomorrowventures.com"),
    ("Tribe Capital", "https://tribecap.co"),
    ("Troika Ventures", "https://www.troikaventures.com"),
    ("TTV Capital", "https://ttvcapital.com"),
    ("Two Bear Capital", "https://www.twobearcapital.com"),
    ("Underscore VC", "https://www.underscore.vc"),
    ("Unusual Ventures", "https://www.unusual.vc"),
    ("Updata Partners", "https://www.updata.com"),
    ("Valor Equity Partners", "https://www.valorep.com"),
    ("ValueAct Capital", "https://www.valueact.com"),
    ("Vamos Ventures", "https://vamosventures.com"),
    ("VantagePoint Capital Partners", "https://www.vpcp.com"),
    ("Vast Ventures", "https://vast.vc"),
    ("VentureFriends", "https://www.venturefriends.vc"),
    ("Vertex Ventures", "https://www.vertexventures.com"),
    ("Vintage Investment Partners", "https://www.vintage-ip.com"),
    ("Viola Ventures", "https://www.viola-group.com"),
    ("WI Harper Group", "https://www.wiharper.com"),
    ("Willoughby Capital", "https://www.willoughbycapital.com"),
    ("Work-Bench", "https://www.work-bench.com"),
    ("XN", "https://www.xn.vc"),
    ("Zephyr Health Ventures", "https://www.zephyrhealthventures.com"),
    ("Zigg Capital", "https://www.ziggcap.com"),
]

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("expand_vc_list")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def slugify(name: str) -> str:
    """Convert VC name to a URL-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


def normalize_url(url: str) -> str:
    """Ensure URL has a scheme."""
    if not url:
        return url
    url = url.strip().rstrip("/")
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def domain_from_url(url: str) -> str:
    """Extract domain from URL."""
    if not url:
        return ""
    try:
        parsed = urlparse(url if "://" in url else f"https://{url}")
        return parsed.netloc.lower().replace("www.", "")
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# VC Data Store
# ---------------------------------------------------------------------------

class VCStore:
    """In-memory store for VC firms, keyed by slug."""

    def __init__(self):
        self.vcs: dict[str, dict] = {}  # slug -> vc dict
        self._domains: set[str] = set()
        self._names_lower: set[str] = set()

    def load_yaml(self, path: Path):
        """Load VCs from vc_list.yaml."""
        if not path.exists():
            log.warning("VC list not found at %s", path)
            return
        with open(path) as f:
            data = yaml.safe_load(f)
        for vc in data.get("vcs", []):
            slug = vc.get("slug") or slugify(vc.get("name", ""))
            if slug:
                self.vcs[slug] = vc
                self._names_lower.add(vc.get("name", "").lower())
                if vc.get("website"):
                    self._domains.add(domain_from_url(vc["website"]))
        log.info("Loaded %d existing VCs from %s", len(self.vcs), path)

    def has_vc(self, name: str, website: str = None) -> bool:
        """Check if we already have this VC."""
        if name.lower() in self._names_lower:
            return True
        if website:
            d = domain_from_url(website)
            if d and d in self._domains:
                return True
        slug = slugify(name)
        return slug in self.vcs

    def add_vc(self, name: str, website: str = None, **kwargs) -> bool:
        """Add a new VC if not duplicate. Returns True if added."""
        if self.has_vc(name, website):
            return False
        slug = slugify(name)
        if not slug:
            return False
        vc = {
            "name": name,
            "slug": slug,
            "website": normalize_url(website) if website else None,
            "focus_sectors": kwargs.get("focus_sectors", ["AI/ML"]),
            "stage_focus": kwargs.get("stage_focus", ["Seed", "Series A"]),
            "hq_region": kwargs.get("hq_region", "Unknown"),
        }
        if kwargs.get("hq_city"):
            vc["hq_city"] = kwargs["hq_city"]
        if kwargs.get("hq_country"):
            vc["hq_country"] = kwargs["hq_country"]
        if kwargs.get("portfolio_urls"):
            vc["portfolio_urls"] = kwargs["portfolio_urls"]
        if kwargs.get("description"):
            vc["description"] = kwargs["description"]
        self.vcs[slug] = vc
        self._names_lower.add(name.lower())
        if website:
            self._domains.add(domain_from_url(website))
        return True

    def set_portfolio_url(self, slug: str, url: str):
        """Set portfolio URL for an existing VC."""
        if slug in self.vcs:
            vc = self.vcs[slug]
            existing = vc.get("portfolio_urls") or []
            if url not in existing:
                vc["portfolio_urls"] = existing + [url]

    def save_yaml(self, path: Path):
        """Write VCs to vc_list.yaml."""
        sorted_vcs = sorted(self.vcs.values(), key=lambda v: v.get("name", "").lower())
        with_portfolio = sum(1 for v in sorted_vcs if v.get("portfolio_urls"))
        header = (
            "# =============================================================================\n"
            "# VC Radar -- VC Firm Registry\n"
            "# =============================================================================\n"
            f"# Auto-generated by scripts/expand_vc_list.py\n"
            f"# Total: {len(sorted_vcs)} VC firms\n"
            f"# VCs with portfolio URL: {with_portfolio}\n"
            "# =============================================================================\n\n"
        )
        data = {"vcs": sorted_vcs}
        yaml_str = yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            f.write(header)
            f.write(yaml_str)
        log.info("Saved %d VCs to %s (%d with portfolio URLs)", len(sorted_vcs), path, with_portfolio)

    @property
    def stats(self) -> dict:
        total = len(self.vcs)
        with_website = sum(1 for v in self.vcs.values() if v.get("website"))
        with_portfolio = sum(1 for v in self.vcs.values() if v.get("portfolio_urls"))
        return {
            "total": total,
            "with_website": with_website,
            "with_portfolio": with_portfolio,
            "without_website": total - with_website,
            "without_portfolio": total - with_portfolio,
        }


# ---------------------------------------------------------------------------
# Scrapers
# ---------------------------------------------------------------------------

def fetch_sync(url: str, timeout: int = REQUEST_TIMEOUT) -> Optional[str]:
    """Synchronous fetch with error handling."""
    import requests
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        log.debug("Failed to fetch %s: %s", url, e)
        return None


def scrape_wikipedia_vc_list(store: VCStore) -> int:
    """Scrape Wikipedia's list of venture capital firms."""
    log.info("Scraping Wikipedia list of venture capital firms...")
    url = "https://en.wikipedia.org/wiki/List_of_venture_capital_firms"
    html = fetch_sync(url)
    if not html:
        log.warning("Failed to fetch Wikipedia VC list")
        return 0

    soup = BeautifulSoup(html, "html.parser")
    added = 0

    # Wikipedia tables contain VC names and sometimes websites
    for table in soup.find_all("table", class_="wikitable"):
        for row in table.find_all("tr")[1:]:  # skip header
            cells = row.find_all(["td", "th"])
            if not cells:
                continue

            # First cell typically has the firm name
            name_cell = cells[0]
            name_link = name_cell.find("a")
            name = name_link.get_text(strip=True) if name_link else name_cell.get_text(strip=True)

            if not name or len(name) < 2:
                continue

            # Try to find website from external links in the row
            website = None
            for cell in cells:
                for a_tag in cell.find_all("a", href=True):
                    href = a_tag["href"]
                    if href.startswith("http") and "wikipedia" not in href and "wikidata" not in href:
                        website = href
                        break
                if website:
                    break

            # Extract HQ/location if available (usually 2nd or 3rd column)
            hq_city = None
            hq_country = None
            if len(cells) >= 3:
                loc_text = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                if "," in loc_text:
                    parts = [p.strip() for p in loc_text.split(",")]
                    hq_city = parts[0]
                    hq_country = parts[-1]

            if store.add_vc(name, website=website, hq_city=hq_city, hq_country=hq_country):
                added += 1
                log.debug("  + Wikipedia: %s (%s)", name, website or "no website")

    log.info("Wikipedia: added %d new VCs", added)
    return added


def scrape_ddg_search(store: VCStore) -> int:
    """Use DuckDuckGo HTML search to find VC lists and scrape them."""
    import requests
    log.info("Searching DuckDuckGo for VC firm lists...")
    added_total = 0

    for query in DDG_QUERIES:
        time.sleep(RATE_LIMIT_SECS + random.uniform(0.5, 1.5))
        log.info("  DDG query: %s", query)

        try:
            resp = requests.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
        except Exception as e:
            log.warning("  DDG search failed: %s", e)
            continue

        soup = BeautifulSoup(resp.text, "html.parser")

        # Extract result links
        result_links = []
        for a_tag in soup.find_all("a", class_="result__a", href=True):
            href = a_tag.get("href", "")
            title = a_tag.get_text(strip=True)
            result_links.append((title, href))

        # Also try result__url class
        for a_tag in soup.find_all("a", class_="result__url", href=True):
            href = a_tag.get("href", "")
            if href not in [r[1] for r in result_links]:
                result_links.append(("", href))

        # Visit top results to extract VC names
        for title, link in result_links[:5]:
            time.sleep(RATE_LIMIT_SECS)
            html = fetch_sync(link)
            if not html:
                continue

            added = _extract_vc_names_from_page(html, store)
            added_total += added
            if added > 0:
                log.info("    Extracted %d new VCs from %s", added, link[:80])

    log.info("DuckDuckGo: added %d new VCs total", added_total)
    return added_total


def _extract_vc_names_from_page(html: str, store: VCStore) -> int:
    """
    Heuristic extraction of VC firm names from an HTML page.
    Looks for patterns like list items, headings, or table cells
    containing names that end with common VC suffixes.
    """
    soup = BeautifulSoup(html, "html.parser")
    added = 0

    # Common VC name suffixes
    vc_suffixes = [
        "ventures", "capital", "partners", "fund", "vc", "equity",
        "investments", "group", "management", "advisors", "labs",
    ]

    # Collect text from likely locations
    candidates = set()

    # List items, table cells, headings, bold/strong text
    for tag in soup.find_all(["li", "td", "th", "h2", "h3", "h4", "strong", "b", "p"]):
        text = tag.get_text(strip=True)
        # Skip very long or very short text
        if len(text) < 3 or len(text) > 80:
            continue
        # Check if it looks like a VC name
        text_lower = text.lower()
        if any(suffix in text_lower for suffix in vc_suffixes):
            # Clean up
            name = re.sub(r"\s*[\(\[].*?[\)\]]", "", text).strip()
            name = re.sub(r"\s*[-–—].*$", "", name).strip()
            name = re.sub(r"^\d+[\.\)]\s*", "", name).strip()  # remove list numbers
            if 3 <= len(name) <= 60 and not any(c in name for c in "{}[]<>"):
                candidates.add(name)

    # Also look for links that point to VC websites
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        text = a_tag.get_text(strip=True)
        if not text or len(text) < 3 or len(text) > 60:
            continue
        text_lower = text.lower()

        # Check if the link text contains VC-like terms
        if any(suffix in text_lower for suffix in vc_suffixes):
            name = text.strip()
            website = href if href.startswith("http") else None
            if store.add_vc(name, website=website):
                added += 1
                continue

        # Check if the URL domain looks like a VC firm
        if href.startswith("http"):
            domain = domain_from_url(href)
            if domain and any(suffix in domain for suffix in ["vc", "ventures", "capital"]):
                if text and not text.startswith("http"):
                    if store.add_vc(text, website=href):
                        added += 1

    # Try the plain text candidates (no website)
    for name in candidates:
        if store.add_vc(name):
            added += 1

    return added


def add_seed_vcs(store: VCStore) -> int:
    """Add well-known VCs from the hardcoded seed list."""
    log.info("Adding seed VCs...")
    added = 0
    for name, website in SEED_VCS:
        if store.add_vc(name, website=website):
            added += 1
    log.info("Seed list: added %d new VCs", added)
    return added


# ---------------------------------------------------------------------------
# Portfolio URL Discovery (async)
# ---------------------------------------------------------------------------

async def discover_portfolio_url(
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    vc: dict,
) -> Optional[str]:
    """
    Given a VC with a website, probe common portfolio page paths.
    Returns the first path that returns HTTP 200, or None.
    """
    website = vc.get("website")
    if not website:
        return None

    base = normalize_url(website).rstrip("/")

    async with semaphore:
        for path in PORTFOLIO_PATHS:
            url = base + path
            try:
                async with session.head(
                    url,
                    timeout=aiohttp.ClientTimeout(total=8),
                    allow_redirects=True,
                    headers=HEADERS,
                ) as resp:
                    if resp.status == 200:
                        # Verify it didn't redirect to homepage
                        final_url = str(resp.url).rstrip("/")
                        base_clean = base.rstrip("/")
                        if final_url != base_clean and final_url != base_clean + "/":
                            log.debug("  Found portfolio: %s -> %s", vc["name"], url)
                            return url
                    # Small delay between path probes
                    await asyncio.sleep(0.3)
            except Exception:
                continue
            await asyncio.sleep(0.3)

        # Also try a GET on /portfolio to check for content
        # (some sites return 200 for all paths but only have content on real pages)
        for path in ["/portfolio", "/companies"]:
            url = base + path
            try:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=8),
                    allow_redirects=True,
                    headers=HEADERS,
                ) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        # Check if the page has substantial content (not just a redirect/404 page)
                        if len(text) > 2000:
                            soup = BeautifulSoup(text, "html.parser")
                            title = soup.title.get_text(strip=True).lower() if soup.title else ""
                            # Skip if it looks like a 404 or generic page
                            if "not found" not in title and "404" not in title:
                                return url
                await asyncio.sleep(0.3)
            except Exception:
                continue

    return None


async def discover_portfolio_urls(store: VCStore):
    """Discover portfolio URLs for all VCs that have a website but no portfolio_url."""
    vcs_to_check = [
        vc for vc in store.vcs.values()
        if vc.get("website") and not vc.get("portfolio_urls")
    ]

    if not vcs_to_check:
        log.info("No VCs need portfolio URL discovery")
        return

    log.info("Discovering portfolio URLs for %d VCs...", len(vcs_to_check))
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    found = 0

    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [
            discover_portfolio_url(session, semaphore, vc)
            for vc in vcs_to_check
        ]

        for i, (vc, coro) in enumerate(zip(vcs_to_check, asyncio.as_completed(tasks))):
            try:
                result = await coro
                if result:
                    store.set_portfolio_url(vc["slug"], result)
                    found += 1
            except Exception as e:
                log.debug("Error discovering portfolio for %s: %s", vc.get("name"), e)

            if (i + 1) % 50 == 0:
                log.info("  Progress: %d/%d checked, %d found", i + 1, len(vcs_to_check), found)

    log.info("Portfolio discovery: found %d new portfolio URLs", found)


# ---------------------------------------------------------------------------
# Website discovery for VCs with no website
# ---------------------------------------------------------------------------

def discover_websites_ddg(store: VCStore) -> int:
    """Use DuckDuckGo to find websites for VCs that have website=None."""
    import requests
    vcs_no_website = [
        vc for vc in store.vcs.values()
        if not vc.get("website")
    ]

    if not vcs_no_website:
        log.info("All VCs have websites")
        return 0

    log.info("Discovering websites for %d VCs via DuckDuckGo...", len(vcs_no_website))
    found = 0

    for vc in vcs_no_website:
        name = vc.get("name", "")
        if not name:
            continue

        time.sleep(RATE_LIMIT_SECS + random.uniform(0.5, 1.0))
        query = f"{name} venture capital official website"

        try:
            resp = requests.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
        except Exception:
            continue

        soup = BeautifulSoup(resp.text, "html.parser")

        # Get the first result URL
        for a_tag in soup.find_all("a", class_="result__a", href=True):
            href = a_tag["href"]
            if href.startswith("http"):
                domain = domain_from_url(href)
                # Skip aggregator sites
                skip_domains = [
                    "crunchbase.com", "linkedin.com", "twitter.com",
                    "wikipedia.org", "pitchbook.com", "cbinsights.com",
                    "google.com", "facebook.com", "youtube.com",
                    "bloomberg.com", "forbes.com",
                ]
                if not any(sd in domain for sd in skip_domains):
                    # Looks like it could be the VC's website
                    parsed = urlparse(href)
                    base_url = f"{parsed.scheme}://{parsed.netloc}"
                    vc["website"] = base_url
                    store._domains.add(domain_from_url(base_url))
                    found += 1
                    log.debug("  Found website for %s: %s", name, base_url)
                    break

        if found % 20 == 0 and found > 0:
            log.info("  Website discovery progress: %d found", found)

    log.info("Website discovery: found %d new websites", found)
    return found


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Expand VC Radar's vc_list.yaml")
    parser.add_argument("--dry-run", action="store_true", help="Don't write output file")
    parser.add_argument("--skip-scrape", action="store_true", help="Skip web scraping for new VCs")
    parser.add_argument("--skip-discovery", action="store_true", help="Skip portfolio URL discovery")
    parser.add_argument("--skip-website-discovery", action="store_true", help="Skip website discovery via DDG")
    parser.add_argument("--max-website-lookups", type=int, default=100, help="Max VCs to search for websites")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    store = VCStore()

    # Step 1: Load existing VCs
    log.info("=" * 60)
    log.info("Step 1: Loading existing VCs")
    log.info("=" * 60)
    store.load_yaml(VC_LIST_PATH)
    log.info("Stats: %s", store.stats)

    # Step 2: Add seed VCs (hardcoded well-known firms)
    log.info("")
    log.info("=" * 60)
    log.info("Step 2: Adding seed VCs")
    log.info("=" * 60)
    add_seed_vcs(store)
    log.info("Stats: %s", store.stats)

    if not args.skip_scrape:
        # Step 3: Scrape Wikipedia
        log.info("")
        log.info("=" * 60)
        log.info("Step 3: Scraping Wikipedia")
        log.info("=" * 60)
        scrape_wikipedia_vc_list(store)
        log.info("Stats: %s", store.stats)

        # Step 4: Scrape DuckDuckGo search results
        log.info("")
        log.info("=" * 60)
        log.info("Step 4: Scraping DuckDuckGo search results")
        log.info("=" * 60)
        scrape_ddg_search(store)
        log.info("Stats: %s", store.stats)

    if not args.skip_website_discovery:
        # Step 5: Discover websites for VCs without them
        log.info("")
        log.info("=" * 60)
        log.info("Step 5: Discovering websites for VCs without them")
        log.info("=" * 60)
        vcs_no_website = [v for v in store.vcs.values() if not v.get("website")]
        if len(vcs_no_website) > args.max_website_lookups:
            log.info(
                "Limiting website lookups to %d of %d VCs",
                args.max_website_lookups, len(vcs_no_website),
            )
            # Shuffle so we don't always look up the same ones
            random.shuffle(vcs_no_website)
            vcs_no_website = vcs_no_website[:args.max_website_lookups]
            # Temporarily mark others so they're skipped
            lookup_names = {v["name"] for v in vcs_no_website}
            original_websites = {}
            for v in store.vcs.values():
                if not v.get("website") and v["name"] not in lookup_names:
                    original_websites[v["slug"]] = None
                    v["website"] = "__skip__"

            discover_websites_ddg(store)

            # Restore skipped ones
            for slug, _ in original_websites.items():
                if store.vcs[slug].get("website") == "__skip__":
                    store.vcs[slug]["website"] = None
        else:
            discover_websites_ddg(store)
        log.info("Stats: %s", store.stats)

    if not args.skip_discovery:
        # Step 6: Discover portfolio URLs
        log.info("")
        log.info("=" * 60)
        log.info("Step 6: Discovering portfolio URLs")
        log.info("=" * 60)
        asyncio.run(discover_portfolio_urls(store))
        log.info("Stats: %s", store.stats)

    # Step 7: Save
    log.info("")
    log.info("=" * 60)
    log.info("Step 7: Saving results")
    log.info("=" * 60)

    if args.dry_run:
        log.info("[DRY RUN] Would save %d VCs", len(store.vcs))
    else:
        # Backup existing file
        if VC_LIST_PATH.exists():
            import shutil
            shutil.copy2(VC_LIST_PATH, BACKUP_PATH)
            log.info("Backed up existing file to %s", BACKUP_PATH)
        store.save_yaml(OUTPUT_PATH)

    # Final summary
    stats = store.stats
    log.info("")
    log.info("=" * 60)
    log.info("FINAL SUMMARY")
    log.info("=" * 60)
    log.info("  Total VCs:           %d", stats["total"])
    log.info("  With website:        %d", stats["with_website"])
    log.info("  With portfolio URL:  %d", stats["with_portfolio"])
    log.info("  Without website:     %d", stats["without_website"])
    log.info("  Without portfolio:   %d", stats["without_portfolio"])


if __name__ == "__main__":
    main()
