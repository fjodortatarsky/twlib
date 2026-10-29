<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" 
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:slim="http://www.loc.gov/MARC21/slim"
	>

  <!-- Identity template -->
  <xsl:template match="@*|node()">
    <xsl:copy>
      <xsl:apply-templates select="@*|node()"/>
    </xsl:copy>
  </xsl:template>

  <xsl:template match="slim:record[slim:datafield[@tag='955']/slim:subfield[@code='n'] = '1'] |
                       slim:record[slim:datafield[@tag='333']/slim:subfield[@code='a'] = 'Исключено из фонда НТБ ТПУ']">
	  <xsl:copy>
		  <xsl:apply-templates select="@*"/>
		  <xsl:apply-templates select="slim:leader"/>
		  <xsl:apply-templates select="slim:controlfield[@tag='001']"/>
		  <xsl:apply-templates select="slim:controlfield[@tag='005']"/>
		  <xsl:apply-templates select="slim:datafield[@tag='035']"/>
		  <xsl:apply-templates select="slim:datafield[@tag='100']"/>
	  </xsl:copy>
	  <xsl:message>Deleted record found (<xsl:value-of select="slim:controlfield[@tag='001']"/>)</xsl:message>
  </xsl:template>

</xsl:stylesheet>

