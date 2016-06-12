# coding=utf-8
from __future__ import unicode_literals

from unittest import TestCase
from xml.dom.minidom import parseString

from polyarchiv.backends import HTTPRequestsStorageBackend

PROPFIND_DATA = """<?xml version="1.0" encoding="utf-8" ?>
   <D:multistatus xmlns:D="DAV:">
     <D:response>
          <D:href>http://www.foo.bar/container/</D:href>
          <D:propstat>
               <D:prop xmlns:R="http://www.foo.bar/boxschema/">
                    <R:bigbox>
                         <R:BoxType>Box type A</R:BoxType>
                    </R:bigbox>
                    <R:author>
                         <R:Name>Hadrian</R:Name>
                    </R:author>
                    <D:creationdate>
                         1997-12-01T17:42:21-08:00
                    </D:creationdate>
                    <D:displayname>
                         Example collection
                    </D:displayname>
                    <D:resourcetype><D:collection/></D:resourcetype>
                    <D:supportedlock>
                         <D:lockentry>
                              <D:lockscope><D:exclusive/></D:lockscope>
                              <D:locktype><D:write/></D:locktype>
                         </D:lockentry>
                         <D:lockentry>
                              <D:lockscope><D:shared/></D:lockscope>
                              <D:locktype><D:write/></D:locktype>
                         </D:lockentry>
                    </D:supportedlock>
               </D:prop>
               <D:status>HTTP/1.1 200 OK</D:status>
          </D:propstat>
     </D:response>
     <D:response>
          <D:href>http://www.foo.bar/container/collection/</D:href>
          <D:propstat>
               <D:prop xmlns:R="http://www.foo.bar/boxschema/">
                    <R:bigbox>
                         <R:BoxType>Box type A</R:BoxType>
                    </R:bigbox>
                    <R:author>
                         <R:Name>Hadrian</R:Name>
                    </R:author>
                    <D:creationdate>
                         1997-12-01T17:42:21-08:00
                    </D:creationdate>
                    <D:displayname>
                         Example collection
                    </D:displayname>
                    <D:resourcetype><D:collection/></D:resourcetype>
                    <D:supportedlock>
                         <D:lockentry>
                              <D:lockscope><D:exclusive/></D:lockscope>
                              <D:locktype><D:write/></D:locktype>
                         </D:lockentry>
                         <D:lockentry>
                              <D:lockscope><D:shared/></D:lockscope>
                              <D:locktype><D:write/></D:locktype>
                         </D:lockentry>
                    </D:supportedlock>
               </D:prop>
               <D:status>HTTP/1.1 200 OK</D:status>
          </D:propstat>
     </D:response>
     <D:response>
          <D:href>http://www.foo.bar/container/front.html</D:href>
          <D:propstat>
               <D:prop xmlns:R="http://www.foo.bar/boxschema/">
                    <D:creationdate>
                         1997-12-01T18:27:21-08:00
                    </D:creationdate>
                    <D:getcontentlength>
                         4525
                    </D:getcontentlength>
                    <D:getlastmodified>
                         Monday, 12-Jan-98 09:25:56 GMT
                    </D:getlastmodified>
                    <D:resourcetype/>
               </D:prop>
               <D:status>HTTP/1.1 200 OK</D:status>
          </D:propstat>
     </D:response>
   </D:multistatus>"""


class WebdavTest(TestCase):
    def test_read_propfind(self):
        url = 'http://www.foo.bar/container/'
        dirnames, filenames = HTTPRequestsStorageBackend.analyze_propfind(url, PROPFIND_DATA)
        self.assertEqual(['collection'], dirnames)
        self.assertEqual(['front.html'], filenames)
