\# Autonomous Incident Triage Agent



\## Deployment



This project can be deployed to Render using the included `render.yaml`.



\### Render Deployment



1\. Push the project to GitHub.

2\. Create a new Web Service on Render.

3\. Connect the GitHub repository.

4\. Render uses `render.yaml` for the deployment configuration.

5\. Set the required environment variables:

&#x20;  - `GEMINI\_API\_KEY`

&#x20;  - `DATABASE\_URL`

6\. Deploy the service.



\### Health Check



The application exposes:



`GET /healthz`



This endpoint can be used to verify that the deployed service is running.



\### Free Tier Notes



The application is designed to support deployment on Render's free tier. Free-tier services may sleep when inactive and may have limited resources.



\## Security



Do not commit `.env` or secrets to the repository. Environment variables should be configured through the deployment platform.

