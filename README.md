# testeng-triggers
Use GitHub webhook events to trigger CI/CD pipeline jobs by inspecting the payload
and making requests to trigger various jenkins jobs.

To test out locally:

Set up a python virtualenv and pip install into it, or install the python requirements globally with:
```
sudo pip install -r requirements.txt
```
Start up the server with something like below.
Note: the www.edx.org value is a placeholder and your actual jenkins URL will be used instead
when the forward proxy script kicks in.
```
mitmdump -s testeng_triggers/testeng_triggers.py -p 8888 -R http://www.edx.org
```

Make a request. Substitue the payload below with your event name that will trigger the logic
that you had coded by modifying the redirect script:
```
curl -X PUT -d '{ "ref": "master", "payload": "{\"user\":\"atmos\",\"room_id\":123456}", "description": "foo" }' http://localhost:8888
```

To deploy on heroku:

* On heroku, follow the instructions for deploying a python app on the cedar stack (free).
* In the heroku app dashboard, under Settings, add Config var values for environment variables that your script needs.
* You can now test out the forward proxy with the above curl statement, using the URL of your heroku app instead
of localhost. Either http or https will work, heroku handles the routing for you.
