#!/bin/bash
#

SCRIPT_PATH="$(realpath "$0")"
SCRIPT_DIR="$(dirname "$SCRIPT_PATH")"

stamp() {
  echo "$1" >>${SCRIPT_DIR}/stamp
}

cd records
if ! yaz-marcdump -i marc -o marcxml -s out -C 2000 koha-bibs.mrc >/dev/null ; then
  echo "Can not split KOHA records for XSLT processing"
  exit 1
fi

for ii in out* ; do
  if ! yaz-marcdump -i marc -o marcxml $ii >$ii.xml ; then
    echo "Can not convert KOHA records to XML"
    exit 1
  fi
done

for ii in out*.xml ; do
  if ! xsltproc ../prepare.xsl $ii >_$ii ; then
    echo "Can not transform KOHA records via XSLT"
    exit 1
  fi
done

if ! yaz-marcdump -i marcxml -o marc _out*.xml >merged.mrc ; then
  echo "Can not merge KOHA records"
  exit 1
fi

rm -f *out*

if ! yaz-marcdump -s out -C 30000 merged.mrc >/dev/null ; then
  echo "Can not split KOHA records for reindex"
  exit 1
fi

rm -f *.mrc

BIBS=`echo *`

for ii in $BIBS ; do
  yaz-marcdump -o marcxml $ii >$ii.xml
  rm $ii
done

cd ..

exit 0


# REINDEX RECORDS

for ii in $BIBS ; do
  if ! docker exec vufind-web-1 /bin/bash -c "cd /usr/local/vufind; cp import/rusmarc.properties import/marc.properties; ./import-marc.sh /opt/ntb/$ii" ; then
    echo "Can not reindex KOHA records $ii"
    sleep 5;
    docker exec vufind-web-1 /bin/bash -c "/etc/init.d/apache2 start"
    sleep 5;
    docker exec vufind-web-1 /bin/bash -c "/etc/init.d/apache2 start"
    sleep 5;
    docker exec vufind-web-1 /bin/bash -c "/etc/init.d/apache2 start"
    exit 1;
  fi
  sync
  stamp "$LINENO: $ii"
done

if [ "$1" = "kohaonly" ] ; then
  docker exec vufind-web-1 /bin/bash -c "/etc/init.d/apache2 start"
  sleep 5;
  docker exec vufind-web-1 /bin/bash -c "/etc/init.d/apache2 start"
  sleep 5;
  docker exec vufind-web-1 /bin/bash -c "/etc/init.d/apache2 start"
  echo "KOHA records indexing DONE. Exiting."
  exit 0;
fi

#if ! docker exec vufind-web-1 /bin/bash -c "cd /usr/local/vufind; cp import/rusmarc.properties import/marc.properties; ./import-marc.sh /opt/ntb/*" ; then
#	echo "Can not reindex KOHA records"
#	exit 1;
#fi

cd /home/fet/NTB/stl-infra/vufind/opt/marc21/SpringerNature_Books_MARC21_20250827_045321/;
for ii in * ; do
  sleep 10;
  if ! docker exec vufind-web-1 /bin/bash -c "cd /usr/local/vufind; cp import/marc21.properties import/marc.properties; ./import-marc.sh /opt/marc21/SpringerNature_Books_MARC21_20250827_045321/$ii" ; then
    echo "Can not reindex SPRINGER records"
    exit 1;
  fi
  stamp "$LINENO: SpringerNature marc21 $ii"
done

#docker compose down web
#docker compose up -d web
#sleep 10;
#if ! docker exec vufind-web-1 /bin/bash -c "cd /usr/local/vufind; cp import/ebs-marc21.properties import/marc.properties; ./import-marc.sh /opt/ebs/Book_Collection_1_MARC_Records.mrc /opt/ebs/Book_Collection_2_MARC_Records.mrc /opt/ebs/AAPT_Book_Archive_MARC_Records.mrc" ; then
#  echo "Can not reindex EBS records"
#  exit 1;
#fi
#stamp "$LINENO AIP book collection"

cd /home/fet/NTB/stl-infra/vufind/opt/ebs/uright/
for ii in * ; do
  docker compose down web
  docker compose up -d web
  sleep 10;
  if ! docker exec vufind-web-1 /bin/bash -c "cd /usr/local/vufind; cp import/ebs-uright.properties import/marc.properties; ./import-marc.sh /opt/ebs/uright/$ii" ; then
    echo "Can not reindex URIGHT $ii records"
    exit 1;
  fi
  stamp "$LINENO uright $ii"
done

cd /home/fet/NTB/stl-infra/vufind/opt/ebs/znanium/
for ii in * ; do
  docker compose down web
  docker compose up -d web
  sleep 10;
  if ! docker exec vufind-web-1 /bin/bash -c "cd /usr/local/vufind; cp import/ebs-znanium.properties import/marc.properties; ./import-marc.sh /opt/ebs/znanium/$ii" ; then
    echo "Can not reindex ZNANIUM $ii records"
    exit 1;
  fi
  stamp "$LINENO znanium $ii"
done

#docker compose down web
#docker compose up -d web
#sleep 10;
#if ! docker exec vufind-web-1 /bin/bash -c "cd /usr/local/vufind; cp import/ebs-ipr.properties import/marc.properties; ./import-marc.sh /opt/ebs/ipr.mrc" ; then
#  echo "Can not reindex IPR records"
#  exit 1;
#fi

docker compose down web
docker compose up -d web
sleep 10;
if ! docker exec vufind-web-1 /bin/bash -c "cd /usr/local/vufind; cp import/ebs-kons.properties import/marc.properties; ./import-marc.sh /opt/ebs/konsultant.mrc" ; then
  echo "Can not reindex kons records"
  exit 1;
fi
stamp "$LINENO consultant"

cd /home/fet/NTB/stl-infra/vufind/opt/ebs/lanbook/
for ii in * ; do
  docker compose down web
  docker compose up -d web
  sleep 10;
  if ! docker exec vufind-web-1 /bin/bash -c "cd /usr/local/vufind; cp import/ebs-lan.properties import/marc.properties; ./import-marc.sh /opt/ebs/lanbook/$ii" ; then
    echo "Can not reindex $ii records"
    exit 1;
  fi
done
stamp "$LINENO lanbook"

sleep 10
docker exec vufind-web-1 /bin/bash -c "/etc/init.d/apache2 start"
sleep 10
docker exec vufind-web-1 /bin/bash -c "/etc/init.d/apache2 start"


