src_dir := custom_components/weatherlink

bump:
	bumpver update --patch

bump_minor:
	bumpver update minor

bump_major:
	bumpver update major
