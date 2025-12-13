# Personal Finance Dashboard

## Overview

This project is a complete, end-to-end personal finance dashboard I built to analyse my spending habits, budgeting patterns, and month-to-month trends. The structure, database fields, categories, and saving space names are tailored specifically to my own setup.

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

<img width="1663" height="912" alt="image" src="https://github.com/user-attachments/assets/c7fb56fb-736d-4db7-9b37-f7b1572db63d" />

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
