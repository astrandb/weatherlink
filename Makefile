src_dir := custom_components/weatherlink

bump:
	bump2version --allow-dirty patch $(src_dir)/const.py $(src_dir)/manifest.json

bump_minor:
	bump2version --allow-dirty minor $(src_dir)/const.py $(src_dir)/manifest.json

bump_major:
	bump2version --allow-dirty major $(src_dir)/const.py $(src_dir)/manifest.json
