# Personal Finance Dashboard

## Overview

This project is a personal finance dashboard I built to analyse my spending habits, budgeting patterns, and month-to-month trends. It is not designed as a plug-and-play tool for others — the structure, database fields, categories, and saving space names are tailored specifically to my own setup.

The system combines a cloud-hosted MongoDB Atlas database with a Dash application deployed on Plotly Cloud. The dashboard provides a clean interface for exploring transactions, my monthly budgeting and financial behaviour, as well as track the growth of my net worth over time.

## Purpose

- Understand spending habits
- Track monthly budgets and savings
- Visualize categories spent, and trends of spending
- Maintain a central personal finance dataset accessible from anywhere
- Experiment with Dash, Plotly and cloud deployment

## Key Features

- Automated retrieval of live bank and investment data using the Starling Bank API and Trading212 API
- Interactive Dash UI with a custom dark theme
- Dynamic filtering (case-insensitive, multi-field search)
- Modular codebase for quick iteration and future expansion
- Hosted on free platforms (MongoDB Atlas + Plotly Cloud)

## Visualizations

<img width="1479" height="824" alt="Screenshot_09-Dec_21-52-35_17672" src="https://github.com/user-attachments/assets/4788f912-1626-4edc-a4f3-9a38e21a4a2d" />

The dashboard currently includes the following visualizations:
- Donut charts for budgeting purposes
- Bar chart to track spending across categories for the current month
- Line charts to track the growth of my savings account and investment portfolio
- Card that displays my net worth as of today
- Monthly transaction table with built-in filtering options (not pictured)

These visualisations were designed specifically to match my personal budgeting workflow.

## Tech Stack 

- Python
- Plotly Dash
- MongoDB Atlas
- Pandas
- Pymongo
- Plotly Cloud (deployment)

## Author

Created and maintained by me, for my own use :) <br>
A small but evolving personal project that helps me stay informed about my finances and experiment with data-driven design.
