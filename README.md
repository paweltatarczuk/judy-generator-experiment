# Experiment for Paweł Tatarczuk's master thesis

Automated generation of unit test data and unit
tests

## What it does?

This experiment uses docker to compare three tools for automatic testing using
EvoSuite's SF110 sample projects in an unified environment.

Experiment compares tests generated with:

- Judy-generator (tool created with Judy v3 for this experiment)
- EvoSuite 1.0.3
- Randoop

(and provided tests with sample projects)

Using following measures:

- line coverage
- instruction coverage
- complexity coverage
- branch coverage
- method coverage
- evosuite mutation analysis
- judy mutation analysis

## Usage

1. Build docker image:

    $ docker build -t experiment .

2. Run image:

\> for all SF110 projects:

Warning! This may take very long time.

    $ docker run --rm experiment

\> for specified SF110 projects:

    $ docker run --rm experiment <test1> <test2>...

For example to run analysis for 34_sbmlreader2 and 53_shp2kml

    $ docker run --rm experiment 34_sbmlreader2 53_shp2kml

3. Read results:

Analysis results will be printed to standard output.
