Scripts that helps to build and maintain Zanata.

## Dependencies

### yum/dnf
Following are the dependencies that can be installed wit yum or dnf.
You can install them through following command:

sudo yum -y install $(sed -n -e '/^===.*dnf/,/^==/ s/^*\(.*\)/\1/p' README.md | xargs)

* cmake-fedora
* fedora-packager
* groovy
* perl-JSON-XS

