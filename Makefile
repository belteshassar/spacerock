help :
	@echo
	@echo "******************************************************************"
	@echo "*   Famous people and the pieces of spacerock named after them   *"
	@echo "*                                                                *"
	@echo "*      To run the file use the command \"make visulize\"           *"
	@echo "******************************************************************"
	@echo

visualize : data.csv edit_counts.csv

data.csv edit_counts.csv : fetch_data.py
	python fetch_data.py
