@Grab(group='com.redhat.victims', module='victims-lib', version='1.3.2')
@Grab(group='com.redhat.victims', module='victims-client', version='1.0-SNAPSHOT')
import com.redhat.victims.*
import com.redhat.victims.database.*
import com.redhat.victims.cli.commands.*
import java.security.MessageDigest
import static groovy.io.FileType.FILES

long time = System.currentTimeMillis()

String checksum(File file) {
  def digest = MessageDigest.getInstance('SHA1')
  file.eachByte(8192) { buffer, length ->
    digest.update(buffer, 0, length)
  }
  new BigInteger(1, digest.digest()).toString(16).padLeft(digest.digestLength << 1, '0')
}

def db = VictimsDB.db()
def cache = new VictimsResultCache()
def dir = new File('./zanata-war/target/zanata/WEB-INF/lib')

//println(new ScanFileCommand().execute(dir.listFiles().collect{it.path}).verboseOutput)

dir.traverse(type: FILES) { f ->

//    println(new ScanFileCommand().execute([f.path]).verboseOutput)
//    return

    String key = checksum(f)
    //println("new key: $key")
    //println("old key: ${checksum0(f)}")
    HashSet<String> cves
    if (cache.exists(key)) {
        //println "found"
        cves = cache.get(key)
    } else {
        ArrayList<VictimsRecord> records = new ArrayList()
        VictimsScanner.scan(f.path, records)
        records.each { record ->
            cves = db.getVulnerabilities(record)
            cache.add(key, cves)
        }
    }
    if (!cves.empty) {
        System.err.println "$f VULNERABLE! $cves"
    } else {
        println "$f OK"
    }
}
println(System.currentTimeMillis() - time)
return
