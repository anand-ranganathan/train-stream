# train-stream

Multimodal transit guide for Connecticut. This web application takes as input a start address and end address, and gives a cost and time based comparison various multi-modal transit options. The two options currently implemented are:
- Direct uber from start to end addresses
- Uber from start address to nearest train station, followed by train ride to station closest to destination and finally an uber trip to the destination from that station. 

## Products
- [App Engine][1]

## Language
- [Python][2]

## APIs
- [Users API][4]
- [Uber API][3]

## Dependencies
- [webapp2][5]
- [jinja2][6]

[1]: https://developers.google.com/appengine
[2]: https://python.org
[3]: https://developer.uber.com/
[4]: https://developers.google.com/appengine/docs/python/users/
[5]: http://webapp-improved.appspot.com/
[6]: http://jinja.pocoo.org/docs/


## Running the app

A Makefile is provided to deploy and run the e2e test on Google App Engine

To run:

     export GAE_PROJECT=your-project-id
     make

To manually run, install the requirements

    pip install -r e2e/requirements-dev.txt

To run locally, using Google App Engine
    dev_appserver.py ./
    And then open
http://localhost:8080/uber_login

To run on Google cloud, use the Makefile (not fully tested yet)

