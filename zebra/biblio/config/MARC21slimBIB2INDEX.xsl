<?xml version="1.0" encoding="UTF-8"?>
<!--
  Индексирование библиографической записи по полю 700/3: идентификатор авторитетной записи
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
       <xsl:call-template name="Local-number"/>
       <xsl:call-template name="Author"/>
       <xsl:call-template name="Title"/>
       <xsl:call-template name="Subject"/>
       <xsl:call-template name="ISBN"/>
       <xsl:call-template name="ISSN"/>
       <xsl:call-template name="Publisher"/>
       <xsl:call-template name="AuthorityAboutCode"/>
       <xsl:call-template name="AuthorityAuthorCode"/>
       <xsl:call-template name="AuthorityCorpCode"/>
       <xsl:call-template name="AuthorityCorpName"/>
       <xsl:call-template name="DateOfPublication"/>
       <xsl:call-template name="any"/>
   </xsl:template>

   <xsl:template name="Local-number">
     <z:index name="Local-number:w Local-number:s Local-number:0">
       <xsl:value-of select="marc:controlfield[@tag='001']"/>
     </z:index>
     <xsl:if test='starts-with(marc:datafield[@tag="035"]/marc:subfield[@code="a"], "(RuTPU)")'>
       <z:index name="Local-number:w Local-number:s Local-number:0">
         <xsl:value-of select='substring-after(marc:datafield[@tag="035"]/marc:subfield[@code="a"], "(RuTPU)")'/>
       </z:index>
     </xsl:if>
     <z:index name="Local-number:w Local-number:s Local-number:u">
       <xsl:value-of select="translate(marc:datafield[@tag='035']/marc:subfield[@code='a'], '{}\', '')"/>
     </z:index>

   </xsl:template>

   <xsl:template name="Title">
     <xsl:for-each select="marc:datafield[@tag='200']/marc:subfield[@code='a'] |
                           marc:datafield[@tag='461']/marc:subfield[@code='t'] |
                           marc:datafield[@tag='462']/marc:subfield[@code='t']">
       <z:index name="Title:w Title:s">
         <xsl:value-of select="."/>
       </z:index>
     </xsl:for-each>
   </xsl:template>

   <xsl:template name="Author">
    <xsl:for-each select="marc:datafield[@tag='700'] |
                          marc:datafield[@tag='701'] |
                          marc:datafield[@tag='702']">
     <z:index name="Author:w Author:s">
       <xsl:value-of select="marc:subfield[@code='a']"/>
       <xsl:text> </xsl:text>
       <xsl:value-of select="marc:subfield[@code='b']"/>
       <xsl:text> </xsl:text>
       <xsl:value-of select="marc:subfield[@code='g']"/>
     </z:index>
     </xsl:for-each>
   </xsl:template>

   <xsl:template name="Subject">
    <xsl:for-each select="marc:datafield[@tag='600'] |
                          marc:datafield[@tag='601'] |
                          marc:datafield[@tag='602'] |
                          marc:datafield[@tag='603'] |
                          marc:datafield[@tag='604'] |
                          marc:datafield[@tag='605'] |
                          marc:datafield[@tag='606'] |
                          marc:datafield[@tag='607'] |
                          marc:datafield[@tag='608'] |
                          marc:datafield[@tag='609'] |
                          marc:datafield[@tag='610'] |
                          marc:datafield[@tag='615'] |
                          marc:datafield[@tag='616']">
     <z:index name="Subject-heading:w Subject-heading:s">
       <xsl:value-of select="marc:subfield"/>
     </z:index>
     </xsl:for-each>
   </xsl:template>

   <xsl:template name="ISBN">
     <z:index name="Identifier-standard:w Identifier-standard:s">
	     <xsl:value-of select="marc:datafield[@tag='010']/marc:subfield"/>
     </z:index>
   </xsl:template>

   <xsl:template name="ISSN">
     <z:index name="ISSN:w ISSN:s">
	     <xsl:value-of select="marc:datafield[@tag='011']/marc:subfield"/>
     </z:index>
   </xsl:template>

   <xsl:template name="Publisher">
     <z:index name="Publisher:w Publisher:s">
	     <xsl:value-of select="marc:datafield[@tag='210']/marc:subfield[@code='c']"/>
     </z:index>
   </xsl:template>

  <xsl:template name="AuthorityAboutCode">
    <xsl:for-each select="marc:datafield[@tag='600']/marc:subfield[@code='9']">
      <z:index name="Authority-about-code:w Authority-about-code:s">
	      <xsl:value-of select="."/>
      </z:index>
    </xsl:for-each>
  </xsl:template>

  <xsl:template name="AuthorityAuthorCode">
    <xsl:for-each select="marc:datafield[@tag='700']/marc:subfield[@code='3'] |
                          marc:datafield[@tag='701']/marc:subfield[@code='3'] |
                          marc:datafield[@tag='702']/marc:subfield[@code='3']">
      <z:index name="Authority-author-code:w Authority-author-code:s">
	      <xsl:value-of select="substring-after(., '(RuTPU)')"/>
      </z:index>
    </xsl:for-each>
    <xsl:for-each select="marc:datafield[@tag='700']/marc:subfield[@code='9'] |
                          marc:datafield[@tag='701']/marc:subfield[@code='9'] |
                          marc:datafield[@tag='702']/marc:subfield[@code='9']">
      <z:index name="Authority-author-code:w Authority-author-code:s">
	      <xsl:value-of select="."/>
      </z:index>
    </xsl:for-each>
  </xsl:template>

  <xsl:template name="AuthorityCorpCode">
    <xsl:for-each select="marc:datafield[@tag='712']/marc:subfield[@code='9']">
      <z:index name="Authority-corp-code:w Authority-corp-code:s">
	      <xsl:value-of select="."/>
      </z:index>
    </xsl:for-each>
  </xsl:template>

  <xsl:template name="AuthorityCorpName">
    <xsl:for-each select="marc:datafield[@tag='712']/marc:subfield[@code='a'] |
                         marc:datafield[@tag='712']/marc:subfield[@code='b']">
      <z:index name="Authority-corp-name:w Authority-corp-name:s">
	      <xsl:value-of select="."/>
      </z:index>
    </xsl:for-each>
  </xsl:template>

  <xsl:template name="DateOfPublication">
    <xsl:for-each select="marc:datafield[@tag='100']/marc:subfield[@code='a']">
        <z:index name="Date-of-publication:w Date-of-publication:s">
	        <xsl:value-of select="substring(., 10, 4)"/>
        </z:index>
    </xsl:for-each>
  </xsl:template>

  <!--xsl:template name="DateOfPublication">
    <xsl:for-each select="marc:datafield[@tag='210']/marc:subfield[@code='d']
    | marc:datafield[@tag='461']/marc:subfield[@code='d'] 
    | marc:datafield[@tag='463']/marc:subfield[@code='d']">
        <z:index name="Date-of-publication:w Date-of-publication:s">
	        <xsl:value-of select="."/>
        </z:index>
    </xsl:for-each>
  </xsl:template-->

   <xsl:template name="any">
     <z:index name="any:w any:s">
	     <xsl:text>allrecords</xsl:text>
     </z:index>

     <xsl:for-each select="marc:datafield[@tag='200']/marc:subfield | 
	                           marc:datafield[@tag='210']/marc:subfield |
	                           marc:datafield[@tag='215']/marc:subfield |
	                           marc:datafield[@tag='330']/marc:subfield |
	                           marc:datafield[@tag='333']/marc:subfield |
	                           marc:datafield[@tag='606']/marc:subfield |
	                           marc:datafield[@tag='608']/marc:subfield |
	                           marc:datafield[@tag='610']/marc:subfield |
	                           marc:datafield[@tag='700']/marc:subfield |
	                           marc:datafield[@tag='701']/marc:subfield |
	                           marc:datafield[@tag='702']/marc:subfield |
	                           marc:datafield[@tag='801']/marc:subfield ">
       <z:index name="any:w any:s">
	       <xsl:value-of select='.'/>
       </z:index>
     </xsl:for-each>
   </xsl:template>

</xsl:stylesheet>
