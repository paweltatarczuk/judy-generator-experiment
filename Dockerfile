FROM debian:jessie

# Download packages
RUN  echo "deb http://ppa.launchpad.net/webupd8team/java/ubuntu xenial main" | tee /etc/apt/sources.list.d/webupd8team-java.list \
  && echo "deb-src http://ppa.launchpad.net/webupd8team/java/ubuntu xenial main" | tee -a /etc/apt/sources.list.d/webupd8team-java.list \
  && apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys EEA14886 \
  && echo debconf shared/accepted-oracle-license-v1-1 select true | debconf-set-selections \
  && echo debconf shared/accepted-oracle-license-v1-1 seen true | debconf-set-selections \
  && apt-get update \
  && apt-get install -y \
    wget \
    unzip \
    git \
    oracle-java8-installer \
    ant \
    python

# Setup workdir
WORKDIR /experiment

# Prepare SF110
RUN wget http://www.evosuite.org/files/SF110-20130704-src.zip \
  && unzip SF110-20130704-src.zip \
  && mv SF110-20130704-src/* . \
  && rmdir SF110-20130704-src \
  && rm SF110-20130704-src.zip

# Download java hamcrest library
RUN wget http://search.maven.org/remotecontent?filepath=org/hamcrest/java-hamcrest/2.0.0.0/java-hamcrest-2.0.0.0.jar -O lib/java-hamcrest-2.0.0.0.jar

# Download evosuite library
RUN wget https://github.com/EvoSuite/evosuite/releases/download/v1.0.3/evosuite-1.0.3.jar -O lib/evosuite-1.0.3.jar

# Install JaCoCo
RUN wget https://oss.sonatype.org/service/local/artifact/maven/redirect?r=snapshots\&g=org.jacoco\&a=jacoco\&e=zip\&v=LATEST -O /tmp/jacoco.zip \
  && unzip /tmp/jacoco.zip lib/jacocoant.jar \
  && rm /tmp/jacoco.zip

# Prepare class lists
RUN ls -1 | grep -P "^\d+_" | while read PROJECT; do find "$PROJECT/src/main/java/" -name *.java | sed "s/$PROJECT\/src\/main\/java\///" | sed "s/\.java$//" | sed "s/\//./g" > "$PROJECT/class.list"; done

# Add custom ant xml
COPY custom-build.xml .
RUN find . -name build.xml -exec perl -0777 -pi -e 's/(<\/project>)/\n  <import file="..\/custom-build.xml" \/>\n$1/' {} \;

# Copy judy libraries
COPY lib lib/

# Copy scripts
COPY scripts/run-evosuite.sh run-evosuite.sh
COPY scripts/run-randoop.sh run-randoop.sh
RUN chmod +x run-evosuite.sh run-randoop.sh

# Setup entrypoint
COPY run.py run.py
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
