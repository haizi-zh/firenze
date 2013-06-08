# coding=utf-8
import string
import re
import common

__author__ = 'Zephyre'

db = None
url = 'http://www.comme-des-garcons.com/commedesgarcons_stores.html'
brand_id = 10096
brandname_e = u'COMME des GARÇONS'
brandname_c = u'川久保玲'


def fetch(level=1, data=None, user='root', passwd=''):
    """

    :param level:
    :param data:
    :param user:
    :param passwd:
    :return:
    """
    try:
        if data is None:
            data = {'url': url}
        html = common.get_data(data['url'])
    except Exception:
        print 'Error occured in getting data: %s' % url
        dump_data = {'level': 1, 'time': common.format_time(), 'data': {'data': url}, 'brand_id': brand_id}
        common.dump(dump_data)
        return []

    db = common.StoresDb()
    db.connect_db(user=user, passwd=passwd)

    sub_pat = re.compile(ur'<!--.*?-->', re.S)
    html = re.sub(sub_pat, '', html)
    split_pos = [m.start() for m in re.finditer(ur'<p><span class="contactboldtitle">', html)]
    split_pos.append(-1)
    sub_list = []
    for i in xrange(len(split_pos) - 1):
        sub_list.append(html[split_pos[i]:split_pos[i + 1]])

    store_list = []
    for sub_html in sub_list:
        entry = common.init_store_entry(brand_id)
        m = re.findall(ur'<span class="contactboldtitle">(.+?)</span>', sub_html)
        if len(m) > 0:
            entry[common.name_l] = m[0]
        m = re.findall(ur'<span class="storethinlines">(.+?)</span>', sub_html, re.S)
        if len(m) >= 2:
            addr = common.reformat_addr(m[0])
            entry[common.addr_l] = addr
            # 城市，国家和邮编
            addr_splits = addr.split(', ')
            term = common.geo_translate(addr_splits[-1])
            # 最后一位是国家
            if len(term) == 0:
                print 'Error in geo translating: %s' % addr_splits[-1]
            else:
                common.update_entry(entry, {common.continent_e: term[common.continent_e],
                                            common.continent_c: term[common.continent_c],
                                            common.country_e: term[common.country_e],
                                            common.country_c: term[common.country_c]})
                m1 = re.findall(ur'(.+?)(\d{3}-\d{4})', addr_splits[-2])
                if len(m1) > 0:
                    common.update_entry(entry, {common.city_e: common.reformat_addr(m1[0][0]),
                                                common.zip_code: m1[0][1]})
                    # 联系方式
            tmp = m[1]
            m1 = re.findall(ur'[\d\-]{5,}', tmp)
            if len(m1) > 0:
                entry[common.tel] = m1[0]
            m1 = re.findall(ur'href="mailto:(.+?@.+?)"', tmp)
            if len(m1) > 0:
                entry[common.email] = m1[0].strip()

        common.chn_check(entry)
        print '%s: Found store: %s, %s (%s, %s)' % (
            brandname_e, entry[common.name_l], entry[common.addr_l], entry[common.country_e],
            entry[common.continent_e])
        db.insert_record(entry, 'stores')
        store_list.append(entry)

    db.disconnect_db()