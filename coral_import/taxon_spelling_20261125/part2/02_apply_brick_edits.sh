set -e
DS=/home/coral/prod/data_store; BK=/home/coral/prod/data_store_backup_taxon_spelling_20261125_part2; NEW=/tmp/taxon_new2_20261125
mkdir -p $BK
while read b old new; do
  [ "$(md5sum < $DS/$b | cut -c1-32)" = "$old" ] || { echo "STOP: $b changed on the hub since it was read"; exit 1; }
  [ "$(md5sum < $NEW/$b | cut -c1-32)" = "$new" ] || { echo "STOP: $b new copy damaged"; exit 1; }
done < $NEW/md5.txt
while read b old new; do
  cp -p $DS/$b $BK/$b
  cat $NEW/$b > $DS/$b
  [ "$(md5sum < $DS/$b | cut -c1-32)" = "$new" ] && [ "$(md5sum < $BK/$b | cut -c1-32)" = "$old" ] || { echo "STOP: $b verify failed"; exit 1; }
done < $NEW/md5.txt
ls -la $BK | wc -l; ls -la $DS/Brick0001670 $DS/Brick0000011; echo APPLIED
