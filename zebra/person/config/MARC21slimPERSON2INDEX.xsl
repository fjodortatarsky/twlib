<?xml version="1.0" encoding="UTF-8"?>
<!--
   Copyright (C) 1995-2013
   Index Data ApS

This file is part of the Zebra server.

Zebra is free software; you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free
Software Foundation; either version 2, or (at your option) any later
version.

Zebra is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
for more details.

You should have received a copy of the GNU General Public License
along with Zebra; see the file LICENSE.zebra.  If not, write to the
Free Software Foundation, 59 Temple Place - Suite 330, Boston, MA
02111-1307, USA.
-->

<xsl:stylesheet
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:z="http://indexdata.com/zebra-2.0"
    xmlns:marc="http://www.loc.gov/MARC21/slim"
    version="1.0">

  <xsl:output indent="yes" method="xml" version="1.0" encoding="UTF-8"/>

  <!-- disable all default text node output -->
  <xsl:template match="text()"/>

  <xsl:template match="/">
    <xsl:if test="marc:collection">
      <collection>
         <xsl:apply-templates select="marc:collection/marc:record"/>
       </collection>
    </xsl:if>
    <xsl:if test="marc:record">
       <xsl:apply-templates select="marc:record"/>
    </xsl:if>
  </xsl:template>


  <!-- match on marcxml record -->
  <xsl:template match="marc:record">
    <xsl:variable name="leader" select="marc:leader"/>
    <xsl:variable name="leader5" select="substring($leader,6,1)"/>
    <xsl:variable name="type">
      <xsl:choose>
         <xsl:when test="$leader5='d'">delete</xsl:when>
         <xsl:otherwise>update</xsl:otherwise>
      </xsl:choose>
    </xsl:variable>
    <xsl:variable name="leader6" select="substring($leader,7,1)"/>
    <xsl:variable name="leader7" select="substring($leader,8,1)"/>
    <xsl:variable name="controlField001"
                  select="normalize-space(marc:controlfield[@tag='001'])"/>
    <xsl:variable name="controlField008"
                  select="normalize-space(marc:controlfield[@tag='008'])"/>

     <xsl:variable name="typeOf008">
       <xsl:choose>
         <xsl:when test="$leader6='a'">
           <xsl:choose>
             <xsl:when test="$leader7='a' or $leader7='c' or $leader7='d'
                             or $leader7='m'">BK</xsl:when>
             <xsl:when test="$leader7='b' or $leader7='i'
                             or $leader7='s'">SE</xsl:when>
           </xsl:choose>
         </xsl:when>
         <xsl:when test="$leader6='t'">BK</xsl:when>
         <xsl:when test="$leader6='p'">MM</xsl:when>
         <xsl:when test="$leader6='m'">CF</xsl:when>
         <xsl:when test="$leader6='e' or $leader6='f'">MP</xsl:when>
         <xsl:when test="$leader6='g' or $leader6='k' or $leader6='o'
                         or $leader6='r'">VM</xsl:when>
         <xsl:when test="$leader6='c' or $leader6='d' or $leader6='i'
                         or $leader6='j'">MU</xsl:when>
       </xsl:choose>
     </xsl:variable>

     <z:record z:id="{$controlField001}" type="{$type}">
       <xsl:call-template name="bib1_rules"/>
     </z:record>
   </xsl:template>

   <xsl:template name="bib1_rules">
       <xsl:call-template name="Localnumber"/>
       <xsl:call-template name="idLichnosti"/>
       <xsl:call-template name="Author1idx"/>
       <xsl:call-template name="Author2idx"/>
       <xsl:call-template name="Author3idx"/>
       <xsl:call-template name="CorpAuthor"/>
       <xsl:call-template name="AuthorSurname"/>
   </xsl:template>



   <xsl:template name="Localnumber">
     <z:index name="Local-number:w Local-number:s Local-number:0">
       <xsl:value-of select="marc:controlfield[@tag='001']"/>
     </z:index>
     <z:index name="Local-number:w Local-number:s Local-number:u">
       <xsl:value-of select="translate(marc:datafield[@tag='035']/marc:subfield[@code='a'], '{}\', '')"/>
     </z:index>
   </xsl:template>


  <xsl:template name="idLichnosti">
    <xsl:for-each select="marc:datafield[@tag='856']/marc:subfield[@code='u']">
      <z:index name="Lichnost-id:w Lichnost-id:s">
	      <xsl:value-of select="substring-after(., 'https://staff.tpu.ru/personal/employee?lid=')"/>
      </z:index>
    </xsl:for-each>
  </xsl:template>

  <xsl:template name="Author1idx">
    <xsl:if test="marc:datafield[@tag='200']/marc:subfield[@code='x'] = 'TPU'">
      <xsl:for-each select="marc:datafield[@tag='200']/marc:subfield[@code='a']">
        <z:index name="Author1idx:w Author1idx:s">
	      <xsl:value-of select="substring(., 1, 1)"/>
        </z:index>
      </xsl:for-each>
    </xsl:if>
  </xsl:template>

  <xsl:template name="Author2idx">
    <xsl:if test="marc:datafield[@tag='200']/marc:subfield[@code='x'] = 'TPU'">
    <xsl:for-each select="marc:datafield[@tag='200']/marc:subfield[@code='a']">
      <z:index name="Author2idx:w Author2idx:s">
	      <xsl:value-of select="substring(., 1, 2)"/>
      </z:index>
    </xsl:for-each>
    </xsl:if>
  </xsl:template>

  <xsl:template name="Author3idx">
    <xsl:if test="marc:datafield[@tag='200']/marc:subfield[@code='x'] = 'TPU'">
      <xsl:for-each select="marc:datafield[@tag='200']/marc:subfield[@code='a']">
      <z:index name="Author3idx:w Author3idx:s">
	      <xsl:value-of select="substring(., 1, 3)"/>
      </z:index>
    </xsl:for-each>
    </xsl:if>
  </xsl:template>

  <xsl:template name="AuthorSurname">
    <xsl:if test="marc:datafield[@tag='200']/marc:subfield[@code='x'] = 'TPU'">
      <xsl:for-each select="marc:datafield[@tag='200']/marc:subfield[@code='a']">
        <z:index name="AuthorSurname:w AuthorSurname:s">
          <xsl:value-of select="."/>
        </z:index>
      </xsl:for-each>
    </xsl:if>
  </xsl:template>

  <xsl:template name="CorpAuthor">
    <xsl:for-each select="marc:datafield[@tag='210']">
      <xsl:if test="marc:subfield[@code='x'] = 'TPU'">
        <xsl:for-each select="marc:subfield[@code='b']">
          <xsl:message><xsl:value-of select="."/></xsl:message>
          <z:index name="CorpAuthor1idx:w CorpAuthor1idx:s">
              <xsl:value-of select="substring(., 1, 1)"/>
          </z:index>
          <z:index name="CorpAuthor2idx:w CorpAuthor2idx:s">
              <xsl:value-of select="substring(., 1, 2)"/>
          </z:index>
          <z:index name="CorpAuthor3idx:w CorpAuthor3idx:s">
              <xsl:value-of select="substring(., 1, 3)"/>
          </z:index>
          <z:index name="CorpAuthor:w CorpAuthor:s">
              <xsl:value-of select="."/>
          </z:index>
        </xsl:for-each>
      </xsl:if>
    </xsl:for-each>
  </xsl:template>


</xsl:stylesheet>
