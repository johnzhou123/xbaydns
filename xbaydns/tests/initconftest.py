#!/usr/bin/env python
# encoding: utf-8
"""
initconftest.py

Created by 黄 冬 on 2007-11-19.
Copyright (c) 2007 __MyCompanyName__. All rights reserved.
"""

import basetest
import logging.config
import os
import pwd
import shutil
import tempfile
import time
import unittest

log = logging.getLogger('xbaydns.tests.initconftest')
logging.basicConfig(level=logging.DEBUG)

from xbaydns.tools import initconf
from xbaydns.conf import sysconf
from xbaydns.utils import shtools

class InitConfTest(basetest.BaseTestCase):
    def setUp(self):
        """初始化测试环境"""
        ostype = os.uname()[0].lower()
        self.named_uid = pwd.getpwnam(sysconf.named_user_map[ostype])[2]
        self.basedir = os.path.realpath(tempfile.mkdtemp(suffix='xbaydns_test'))
        basetest.BaseTestCase.setUp(self)

    def tearDown(self):
        """清洁测试环境"""
        shutil.rmtree(self.basedir)
        basetest.BaseTestCase.tearDown(self)

    def test_acl_file(self):
        """测试acl_file调用"""
        acl_content = initconf.acl_file( dict(cnc=('192.168.1.1', '202.106.1.1')) )
        #log.debug("acl content is:" + acl_content)
        self.assertEqual(acl_content,'acl "cnc" { 192.168.1.1; 202.106.1.1; };\n')

    def _create_dir(self, *path):
        cur = self.basedir
        for part in path:
            cur = os.path.join(cur, part)
            os.mkdir(cur)
        return cur[len(self.basedir) + 1:]

    def _create_file(self, *path):
        filename = os.path.join(self.basedir, *path)
        fd = file(filename, 'w')
        fd.close()
        return filename[len(self.basedir) + 1:]

    def test_muti_acl_file(self):
        """test muti record acl acl_file"""
        acl_content = initconf.acl_file( dict(
            cnc=('1.1.1.1','2.2.2.2','3.3.3.3'),
            telcom=('4.4.4.4','5.5.5.5') ))
        self.assertEqual(acl_content,'acl "telcom" { 4.4.4.4; 5.5.5.5; };\nacl "cnc" { 1.1.1.1; 2.2.2.2; 3.3.3.3; };\n')

    def test_defaultzone_file(self):
        """defaultzone_file test"""
        defaultzone = initconf.defaultzone_file()
        #log.debug("defaultzone is:%s"%defaultzone)
        self.assertTrue( 'zone "." { type hint; file "named.root"; };' in defaultzone )
    
    def test_error_default_file(self):
        curset = initconf.TMPL_DEFAULTZONE
        initconf.TMPL_DEFAULTZONE = "中华人民共和国"
        returncode = initconf.defaultzone_file()
        initconf.TMPL_DEFAULTZONE = curset
        self.assertFalse( returncode )

    def test_named_root_file(self):
        """named_root_file test"""
        rootfile = initconf.named_root_file()
        self.assertTrue('A.ROOT-SERVERS.NET.      3600000      A' in rootfile )

    def test_error_named_root_file(self):
        """对于named_root_file的错误调用测试"""
        curset = initconf.TMPL_NAMEDROOT
        initconf.TMPL_NAMEDROOT = "中华人民共和国"
        returncode =  initconf.named_root_file()
        initconf.TMPL_NAMEDROOT = curset
        self.assertFalse(returncode)

    def test_error_backup_conf(self):
        """对于backup_conf的错误调用测试"""
        self.assertFalse( initconf.backup_conf("中华人民共和国","中华人民共和国") )

    def test_backup_conf(self):
        """测试backup_conf的调用"""
        tmpdir = self._create_dir("backuptest")
        self.assertTrue( initconf.backup_conf("/var/named",os.path.join(self.basedir,tmpdir)) )
        conffilename = "namedconf_%s.tar.bz2"%(time.strftime("%y%m%d%H%M"))
        log.debug("backup file is:%s"%(os.path.join(self.basedir,tmpdir,conffilename)))
        self.assertTrue( os.path.isfile(os.path.join(self.basedir,tmpdir,conffilename)) )

    def test_create_destdir(self):
        """测试create_destdir的调用"""
        tmpdir = initconf.create_destdir("/etc/namedconf", self.named_uid)
        log.debug("create tmpdir is:%s"%tmpdir)
        self.assertTrue( os.path.isdir("%s/etc/namedconf/acl"%tmpdir) )
        self.assertTrue( os.path.isdir("%s/etc/namedconf/dynamic"%tmpdir) )
        self.assertTrue( os.path.isdir("%s/etc/namedconf/master"%tmpdir) )
        self.assertTrue( os.path.isdir("%s/etc/namedconf/slave"%tmpdir) )
        shutil.rmtree(tmpdir)

    def test_create_conf(self):
        """测试create_conf的调用"""
        tmpdir = initconf.create_destdir("/etc/namedconf", self.named_uid)
        self.assertTrue( initconf.create_conf("/etc/namedconf", tmpdir) )
        shutil.rmtree(tmpdir)
        
    def test_namedconf_file(self):
        """测试namedconf_file的调用"""
        namedconf = initconf.namedconf_file("/etc/namedconf", dict(acl='acl/acldef.conf', defzone='defaultzone.conf'))
        #log.debug("namedconf gen to:%s"%namedconf)
        self.assertTrue('include "defaultzone.conf";' in namedconf)
        self.assertTrue('include "acl/acldef.conf";' in namedconf)

    def test_install_conf(self):
        """测试install_conf的调用"""
        tmpdir = initconf.create_destdir("/etc/namedconf", self.named_uid)
        chrootdir = os.path.realpath(self._create_dir("namedchroot"))
        real_confdir = os.path.join(chrootdir, "etc/namedconf")
        self.assertTrue( initconf.create_conf("/etc/namedconf", tmpdir) )
        self.assertTrue(initconf.install_conf(tmpdir, "namedchroot", os.path.join(self.basedir,real_confdir)) )
        self.assertTrue( os.path.isfile(os.path.join(real_confdir,"named.conf")) )
        
    def test_check_conf(self):
        '''使用named-checkconf检查生成文件语法'''
        tmpdir = initconf.create_destdir("/etc/namedconf", self.named_uid)
        self.assertTrue(initconf.create_conf("/etc/namedconf", tmpdir))
        ret = shtools.execute(executable = "named-checkconf", args = "-t %s /%s/named.conf"%(tmpdir, "/etc/namedconf"), output="/tmp/hd.txt")
        self.assertEqual(ret, 0)
        
def suite():
    """集合测试用例"""
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(InitConfTest, 'test'))
    return suite

"""
单独运行command的测试用例
"""
if __name__ == '__main__':
    unittest.main(defaultTest='suite')
