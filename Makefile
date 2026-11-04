.PHONY: all data clean train drift test
all: data clean train drift
data:
	python data/generate_data.py --n 10000 --seed 42 --out data/raw/applications.csv
	python data/generate_data.py --n 3000 --seed 7 --drift 1.0 --out data/raw/applications_2026q1.csv
clean:
	python -m src.clean
train:
	python -m src.train
drift:
	python -m src.monitor data/raw/applications.csv data/raw/applications_2026q1.csv
test:
	python -m pytest -q
