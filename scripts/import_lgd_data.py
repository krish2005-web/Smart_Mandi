"""Import official LGD CSV exports. Expected CSVs can be supplied as --states, --districts, --subdistricts, --villages.
Column names vary by LGD export, so map them in normalize_row() after downloading the current files from the official OGD/LGD portal.
This script deliberately refuses to claim demo data is authoritative.
"""
import argparse,csv
from app import create_app
from app.extensions import db
from app.models import State,District,Block,Village

def rows(path):
    with open(path,encoding='utf-8-sig',newline='') as f: yield from csv.DictReader(f)
def pick(row,*names):
    for n in names:
        if n in row and row[n]: return row[n].strip()
    return None

def main():
    p=argparse.ArgumentParser();p.add_argument('--states');p.add_argument('--districts');p.add_argument('--subdistricts');p.add_argument('--villages');a=p.parse_args()
    app=create_app()
    with app.app_context():
        if a.states:
            for r in rows(a.states):
                name=pick(r,'State Name','state_name','STATE_NAME');code=pick(r,'LGD State Code','state_code','STATE_CODE')
                if name and not State.query.filter_by(lgd_code=code).first():db.session.add(State(name=name,lgd_code=code))
            db.session.commit()
        if a.districts:
            for r in rows(a.districts):
                code=pick(r,'LGD District Code','district_code','DISTRICT_CODE');name=pick(r,'District Name','district_name','DISTRICT_NAME');scode=pick(r,'LGD State Code','state_code','STATE_CODE');s=State.query.filter_by(lgd_code=scode).first()
                if s and name and not District.query.filter_by(lgd_code=code).first():db.session.add(District(name=name,lgd_code=code,state_id=s.id))
            db.session.commit()
        if a.subdistricts:
            for r in rows(a.subdistricts):
                code=pick(r,'LGD Sub-District Code','subdistrict_code','SUBDISTRICT_CODE');name=pick(r,'Sub-District Name','subdistrict_name','SUBDISTRICT_NAME');dcode=pick(r,'LGD District Code','district_code','DISTRICT_CODE');d=District.query.filter_by(lgd_code=dcode).first()
                if d and name and not Block.query.filter_by(lgd_code=code).first():db.session.add(Block(name=name,lgd_code=code,district_id=d.id))
            db.session.commit()
        if a.villages:
            for r in rows(a.villages):
                code=pick(r,'LGD Village Code','village_code','VILLAGE_CODE');name=pick(r,'Village Name','village_name','VILLAGE_NAME');bcode=pick(r,'LGD Sub-District Code','subdistrict_code','SUBDISTRICT_CODE');b=Block.query.filter_by(lgd_code=bcode).first();panch=b.panchayats[0] if b and b.panchayats else None
                if b and panch and name and not Village.query.filter_by(lgd_code=code).first():db.session.add(Village(name=name,lgd_code=code,panchayat_id=panch.id))
            db.session.commit()
if __name__=='__main__':main()
